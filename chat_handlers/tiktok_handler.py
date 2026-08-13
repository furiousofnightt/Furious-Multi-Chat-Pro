from urllib.parse import quote, urlencode

from TikTokLive import TikTokLiveClient
import TikTokLive.events as TikTokEvents
from TikTokLive.events import (
    CommentEvent, ConnectEvent, DisconnectEvent, GiftEvent, FollowEvent,
    ShareEvent, RoomUserSeqEvent, LikeEvent, JoinEvent, EmoteChatEvent,
    SocialEvent, UnknownEvent, BarrageEvent,
    WebsocketResponseEvent
)

CommentsEvent = getattr(TikTokEvents, "CommentsEvent", None)
EcBarrageEvent = getattr(TikTokEvents, "EcBarrageEvent", None)

try:
    from TikTokLive.client.errors import InitialCursorMissingError, WebsocketURLMissingError
    import TikTokLive.client.ws.ws_utils as _ws_utils
    import TikTokLive.client.ws.ws_connect as _ws_connect

    def _patched_build_webcast_uri(initial_webcast_response, base_uri_params, base_uri_append_str):
        if not initial_webcast_response.cursor:
            raise InitialCursorMissingError("Missing cursor in initial fetch response.")
        if not initial_webcast_response.push_server:
            raise WebsocketURLMissingError("No websocket URL received from TikTok.")
        if not initial_webcast_response.route_params:
            raise WebsocketURLMissingError("Websocket parameters missing.")

        uri_params = {
            **{k: v for k, v in initial_webcast_response.route_params.items() if v is not None},
            **{k: v for k, v in base_uri_params.items() if v is not None},
        }
        uri_params = {k: str(v) for k, v in uri_params.items()}
        return (
            initial_webcast_response.push_server
            + "?"
            + urlencode(uri_params, safe='', quote_via=quote)
            + base_uri_append_str
        )

    _ws_utils.build_webcast_uri = _patched_build_webcast_uri
    _ws_connect.build_webcast_uri = _patched_build_webcast_uri
except Exception as _patch_exc:
    print(f"⚠️ TikTokLive websocket URI patch not applied: {_patch_exc}")

from .base_handler import BaseChatHandler
from utils.emoticons import convert_emoticons, get_emote_url
from utils.translations import get_translation
from utils.resource_path import resource_path
from TikTokLive.proto.custom_proto import ExtendedUser
import asyncio
import base64
import httpx
import time
import os
import traceback


class TikTokHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "tiktok"
        self.client = None
        self.loop = None
        self._msg_history = []
        self._rate_limited = False
        self._connected_event = None
        self._avatar_b64_cache = {}  # {user_id: "<img ...>"} — persiste entre reconexões

    def start_with_loop(self, loop):
        self.loop = loop
        self.is_running = True
        self._reconnect_attempts = 0
        async def run_tiktok_once():
            try:
                # Lê o sessionid salvo nas configurações (via login do mini-navegador)
                from core.settings_manager import SettingsManager

                # Autoriza o envio do SessionID para o servidor de assinaturas padrão (Euler Stream)
                # Necessário na v6.6.6+ do TikTokLive para não bloquear a conexão por segurança
                os.environ["WHITELIST_AUTHENTICATED_SESSION_ID_HOST"] = "api.eulerstream.com"

                session_id = None
                try:
                    settings_manager = SettingsManager()
                    session_id = settings_manager.settings.get('tiktok_session_id', '')
                except Exception:
                    session_id = None

                kwargs = {
                    'unique_id': self.username,
                    'ws_kwargs': {
                        'open_timeout': 10.0,
                        'ping_interval': None,
                        'ping_timeout': None,
                        'close_timeout': 5.0,
                    }
                }

                if session_id:
                    print(f"[TikTok] Usando sessionid salvo ({len(session_id)} chars) para autenticacao.")
                    kwargs['web_kwargs'] = {'httpx_kwargs': {'cookies': {'sessionid': session_id}}}
                else:
                    print("[TikTok] Nenhum sessionid encontrado. Lives +18 nao terao uptime real.")

                self.client = TikTokLiveClient(**kwargs)

                self._already_connected = False
                self._create_time = None
                self._total_likes = 0
                self._total_views = 0
                self._room_info_fetched = False
                self._gift_icon_cache = {}
                self._gift_b64_cache = {}

                async def _build_gift_cache():
                    """Busca a lista de presentes do TikTok e monta o cache de URLs de ícones."""

                    try:
                        data = await self.client.web.fetch_gift_list()
                        gifts = data.get('gifts', data) if isinstance(data, dict) else (data or [])
                        if isinstance(gifts, list):
                            for g in gifts:
                                name = (g.get('name') or '').lower()
                                img = g.get('image') or {}
                                icon = g.get('icon') or {}
                                
                                # A V6 usa chaves diferentes (ex: url_list, m_urls)
                                img_urls = img.get('url_list') or img.get('url_urls') or img.get('m_urls') or [None]
                                icon_urls = icon.get('url_list') or icon.get('url_urls') or icon.get('m_urls') or [None]
                                
                                url = (
                                    img_urls[0]
                                    or g.get('icon_url')
                                    or g.get('cover_url')
                                    or icon_urls[0]
                                )
                                if name and url:
                                    self._gift_icon_cache[name] = url
                        print(f"✅ Gift icon cache: {len(self._gift_icon_cache)} presentes")
                    except Exception as e:
                        print(f"⚠️ Gift cache falhou: {e}")

                async def _get_gift_icon_html(gift_name: str) -> str:
                    """Retorna a tag <img> Base64 para o ícone do presente. Usa cache para não baixar repetido."""
                    key = gift_name.lower()
                    if key in self._gift_b64_cache:
                        return self._gift_b64_cache[key]
                    icon_url = self._gift_icon_cache.get(key, '')
                    if not icon_url:
                        return ''
                    try:
                        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tiktok.com/"}
                        async with httpx.AsyncClient(timeout=5.0, headers=headers) as hc:
                            resp = await hc.get(icon_url)
                            if resp.status_code == 200 and resp.content:
                                b64 = base64.b64encode(resp.content).decode()
                                ct = resp.headers.get("content-type", "image/png")
                                html = f"<img src='data:{ct};base64,{b64}'>"
                                self._gift_b64_cache[key] = html
                                return html
                    except Exception:
                        pass
                    return ''

                async def _get_avatar_b64(user_obj) -> str:
                    """Retorna tag <img> com avatar Base64 do usuário. Cache por user_id."""
                    try:
                        user_id = str(getattr(user_obj, 'id', '') or '')
                        if not user_id:
                            return ''
                        # Sentinel: None = download em andamento, '' = falhou, '<img>' = ok
                        cached = self._avatar_b64_cache.get(user_id, 'NOT_FOUND')
                        if cached != 'NOT_FOUND':
                            return cached or ''
                        # Marca como em andamento antes de qualquer await
                        self._avatar_b64_cache[user_id] = None
                        avatar_url = None
                        avatar_thumb = getattr(user_obj, 'avatar_thumb', None)
                        if avatar_thumb:
                            url_list = getattr(avatar_thumb, 'url_list', None)
                            if url_list and len(url_list) > 0:
                                avatar_url = url_list[0]
                        if not avatar_url:
                            self._avatar_b64_cache[user_id] = ''
                            return ''
                        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tiktok.com/"}
                        async with httpx.AsyncClient(timeout=5.0, headers=headers) as hc:
                            resp = await hc.get(avatar_url)
                            if resp.status_code == 200 and resp.content:
                                b64 = base64.b64encode(resp.content).decode()
                                ct = resp.headers.get("content-type", "image/jpeg")
                                tag = (f"<img src='data:{ct};base64,{b64}' "
                                       f"width='22' height='22' "
                                       f"style='border-radius:50%;vertical-align:middle;margin-right:3px;'>")
                                self._avatar_b64_cache[user_id] = tag
                                # Limpar cache se ficar grande demais (~500 avatares)
                                if len(self._avatar_b64_cache) > 500:
                                    keys = list(self._avatar_b64_cache.keys())
                                    for k in keys[:250]:
                                        del self._avatar_b64_cache[k]
                                return tag
                        # Download falhou
                        self._avatar_b64_cache[user_id] = ''
                    except Exception:
                        # Garante que o sentinel None nunca fica preso em caso de erro
                        try:
                            user_id2 = str(getattr(user_obj, 'id', '') or '')
                            if user_id2 and self._avatar_b64_cache.get(user_id2) is None:
                                self._avatar_b64_cache[user_id2] = ''
                        except Exception:
                            pass
                    return ''

                def _get_badge_str(user_obj) -> str:
                    """Retorna HTML com badges TikTok como <img> de SVG local. Nunca levanta exceção."""
                    badges = ''
                    try:
                        def badge_img(svg_name):
                            path = resource_path(f'assets/{svg_name}').replace('\\', '/')
                            return (f" <img src='file:///{path}' "
                                    f"width='16' height='16' "
                                    f"style='vertical-align:middle;margin-left:2px;'>")
                        
                        is_mod = False
                        is_top_gifter = False
                        is_fan = False
                        is_host = False
                        is_sub = False
                        is_friend = False
                        is_pro = False
                        
                        # Fix for TikTokLive v6 bug: 'badges' vs 'badge_list'
                        badge_list = getattr(user_obj, 'badge_list', []) or []
                        if not badge_list:
                            # Fallback para versões antigas
                            badge_list = getattr(user_obj, 'badges', []) or []
                            
                        for b in badge_list:
                            try:
                                scene_name = str(getattr(getattr(b, 'scene_type', None), 'name', '') or '').upper()
                                scene_value = getattr(getattr(b, 'scene_type', None), 'value', -1)
                                if scene_name == 'ADMIN' or scene_value == 1:
                                    is_mod = True
                                elif 'RANK_LIST' in scene_name or scene_value == 6:
                                    is_top_gifter = True
                                elif scene_name == 'FANS' or scene_value == 10:
                                    is_fan = True
                                elif scene_name == 'ANCHOR' or scene_value == 12:
                                    is_host = True
                                elif scene_name == 'SUBSCRIBER' or scene_name == 'NEW_SUBSCRIBER' or scene_value in (4, 7):
                                    is_sub = True
                                elif scene_name == 'FRIENDS' or scene_value == 3:
                                    is_friend = True
                                elif scene_name == 'LIVE_PRO' or scene_value == 11:
                                    is_pro = True
                            except Exception:
                                pass

                        if getattr(user_obj, 'verified', False):
                            badges += badge_img('tiktok_verified.svg')
                        if is_host:
                            badges += badge_img('tiktok_host.svg')
                        if is_mod or getattr(user_obj, 'is_moderator', False):
                            badges += badge_img('tiktok_mod.svg')
                        if is_pro:
                            badges += badge_img('tiktok_live_pro.svg')
                        if is_sub:
                            badges += badge_img('tiktok_sub.svg')
                        if is_top_gifter or getattr(user_obj, 'is_top_gifter', False):
                            badges += badge_img('tiktok_top_gifter.svg')
                        if is_friend:
                            badges += badge_img('tiktok_friend.svg')
                        
                        member_lvl = getattr(user_obj, 'member_level', None)
                        if is_fan or (member_lvl and str(member_lvl).isdigit() and int(member_lvl) > 0):
                            badges += badge_img('tiktok_fan.svg')
                    except Exception:
                        pass
                    return badges

                async def _sync_uptime_background():
                    """Busca uptime em background sem bloquear o event loop de mensagens."""
                    try:
                        import re
                        url = f"https://www.tiktok.com/@{self.username}/live"
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                        async with httpx.AsyncClient(timeout=10.0, headers=headers) as hc:
                            resp = await hc.get(url)
                            if resp.status_code == 200:
                                # FIX #5: Regex aceita 10 a 13 dígitos (suporta timestamps em ms)
                                m = re.search(r'\"(?:startTime|createTime|create_time)\":(\d{10,13})', resp.text)
                                if m:
                                    ts = int(m.group(1))
                                    # Normalizar para segundos se vier em milissegundos
                                    if ts > 9_999_999_999:
                                        ts //= 1000
                                    self._create_time = ts
                                    self._room_info_fetched = True
                                    print(f"✅ Uptime sincronizado via HTML Scraping! (ts={ts})")
                                    
                                m_likes = re.search(r'\"like_count\":\s*(\d+)|\"likeCount\":\s*(\d+)', resp.text)
                                if m_likes and self._total_likes == 0:
                                    self._total_likes = int(m_likes.group(1) or m_likes.group(2))
                                    print(f"✅ Likes iniciais sincronizados via HTML! ({self._total_likes})")
                                    # Força atualização na UI
                                    viewers = getattr(self.client, 'viewer_count', 0)
                                    uptime_s = max(0, int(time.time()) - (self._create_time or int(time.time())))
                                    self.stats_updated.emit(viewers, uptime_s, self._total_likes, getattr(self, '_total_views', 0))
                                    
                                if m: return
                        # Fallback: Web API
                        rid = getattr(self.client, 'room_id', None)
                        r_dict = await self.client.web.fetch_room_info(room_id=rid)
                        if isinstance(r_dict, dict):
                            ct = r_dict.get('create_time') or r_dict.get('createTime') or r_dict.get('start_time')
                            if not ct:
                                room = r_dict.get('room', r_dict.get('data', {}).get('room', {}))
                                if isinstance(room, dict):
                                    ct = room.get('create_time') or room.get('createTime')
                            if ct:
                                v = int(ct)
                                if v > 9_999_999_999: v //= 1000
                                self._create_time = v
                                self._room_info_fetched = True
                                print(f"✅ Uptime sincronizado via Web API! (ts={v})")
                    except:
                        pass

                @self.client.on(LikeEvent)
                async def on_like(event: LikeEvent):
                    self._total_likes = getattr(event, 'total', getattr(event, 'total_likes', self._total_likes))
                    uptime_seconds = int(time.time()) - (self._create_time or int(time.time()))
                    viewers = getattr(self.client, 'viewer_count', 0)
                    self.stats_updated.emit(viewers, max(0, uptime_seconds), self._total_likes, getattr(self, '_total_views', 0))

                @self.client.on(RoomUserSeqEvent)
                async def on_user_seq(event: RoomUserSeqEvent):
                    viewers = getattr(event, 'total', getattr(event, 'viewer_count', getattr(event, 'm_total', 0)))
                    self._total_views = getattr(event, 'total_user', getattr(event, 'total_user_count', getattr(self, '_total_views', 0)))

                    # FIX #2+#3: Sincronização de Uptime com debounce e sem bloquear o event loop
                    # Só dispara a busca se não temos o tempo E se passaram 30s desde a última tentativa
                    now = time.time()
                    if not self._create_time and (now - getattr(self, '_last_uptime_attempt', 0)) > 30:
                        self._last_uptime_attempt = now

                        # Primeiro tenta via objeto interno (instantâneo, sem I/O)
                        try:
                            internal_info = getattr(self.client, 'room_info', None)
                            if internal_info:
                                ct = getattr(internal_info, 'create_time',
                                     getattr(internal_info, 'createTime',
                                     getattr(internal_info, 'create_timestamp',
                                     getattr(internal_info, 'start_time', None))))
                                if ct:
                                    v = int(ct)
                                    if v > 2000000000: v //= 1000
                                    self._create_time = v
                                    self._room_info_fetched = True
                                    print(f"✅ Uptime sincronizado via Canal Binário!")
                        except:
                            pass

                        # Se não achou, dispara o scraping HTTP em tarefa separada (não bloqueia o loop)
                        if not self._create_time:
                            asyncio.create_task(_sync_uptime_background())

                    # Cálculo do uptime
                    current_start = self._create_time or getattr(self, '_start_ts', int(time.time()))
                    uptime_seconds = max(0, int(time.time()) - current_start)
                    self.stats_updated.emit(viewers, uptime_seconds, self._total_likes, getattr(self, '_total_views', 0))

                def _emit_if_new(author, msg, author_display=None):
                    now = time.time()
                    msg_key = f"{author}::{msg}"  # chave de dedup usa sempre o nome puro
                    
                    if not hasattr(self, "_msg_history_dict"):
                        self._msg_history_dict = {}
                        
                    if msg_key in self._msg_history_dict:
                        # Se a mesma mensagem chegou em menos de 3 segundos, é o bug de evento duplicado da API do TikTok
                        # Se demorou mais que 3 segundos, foi o usuário que digitou novamente de propósito!
                        if now - self._msg_history_dict[msg_key] < 3.0:
                            return
                            
                    self._msg_history_dict[msg_key] = now
                    
                    # Limpa o dicionário de tempos em tempos para não gastar memória RAM
                    if len(self._msg_history_dict) > 100:
                        self._msg_history_dict = {k: v for k, v in self._msg_history_dict.items() if now - v < 10.0}
                    
                    # author_display pode conter <img> de avatar/badges; author é sempre o nome puro
                    emit_author = author_display if author_display is not None else author
                    self.message_received.emit(emit_author, msg, "tiktok")

                # FIX #1: on_comment blindado — nenhuma mensagem se perde silenciosamente
                @self.client.on(CommentEvent)
                async def on_comment(event: CommentEvent):
                    try:
                        raw = (getattr(event, 'comment', None)
                               or getattr(event, 'message', None)
                               or getattr(event, 'text', None)
                               or "")
                        
                        has_emotes = bool(getattr(event, 'emotes', None))
                        
                        # Só descarta se não tiver texto E não tiver emotes customizados
                        if not raw and not has_emotes:
                            return  # Mensagem genuinamente vazia
                        
                        raw = str(raw) if raw else ""
                        
                        # 🔥 Emojis Customizados do TikTok
                        if getattr(event, 'emotes', None):
                            try:
                                emotes_to_process = []
                                for e in event.emotes:
                                    emote_obj = getattr(e, 'emote', None)
                                    idx = getattr(e, 'index', -1)
                                    if emote_obj and idx >= 0:
                                        emotes_to_process.append((idx, emote_obj))
                                
                                # De trás pra frente para manter a validade dos índices
                                emotes_to_process.sort(key=lambda x: x[0], reverse=True)
                                
                                for idx, emote_obj in emotes_to_process:
                                    img_obj = getattr(emote_obj, 'image', None)
                                    if not img_obj: continue
                                    urls = getattr(img_obj, 'url_list', [])
                                    if not urls: continue
                                    
                                    img_url = str(urls[0])
                                    emote_id = str(getattr(emote_obj, 'emote_id', 'unknown'))
                                    
                                    # Roda de forma async (via thread do executor) para não bloquear o loop do TikTok
                                    local_url = await asyncio.get_event_loop().run_in_executor(
                                        None, get_emote_url, img_url, f"ttk_{emote_id}"
                                    )
                                    
                                    if local_url:
                                        img_tag = f"<img src='{local_url}' width='22' height='22' style='vertical-align: middle; margin: 0 1px;'>"
                                        
                                        # Se existe um placeholder [...] na posição indicada, nós o substituímos.
                                        if idx < len(raw) and raw[idx] == '[':
                                            end_idx = raw.find(']', idx)
                                            if end_idx != -1:
                                                raw = raw[:idx] + img_tag + raw[end_idx+1:]
                                            else:
                                                raw = raw[:idx] + img_tag + raw[idx:]
                                        else:
                                            # Fallback, insere na posição exata
                                            raw = raw[:idx] + img_tag + raw[idx:]
                            except Exception as em_e:
                                print(f"⚠️ Erro ao processar emotes customizados do TikTok: {em_e}")

                        msg = convert_emoticons(raw)

                        # user / user_info contains the raw proto User
                        user_obj = getattr(event, 'user', None) or getattr(event, 'user_info', None)

                        author = "Usuário"
                        try:
                            if user_obj:
                                author = (getattr(user_obj, 'nick_name', None)
                                          or getattr(user_obj, 'nickname', None)
                                          or getattr(user_obj, 'username', None)
                                          or "Usuário")
                        except:
                            pass

                        # Avatar: cache hit = instant; novo usuário = aguarda até 1s (asyncio.shield
                        # não bloqueia outros eventos, apenas dá tempo ao CDN que é rápido)
                        avatar_html = ''
                        user_id = ''
                        try:
                            if user_obj:
                                user_id = str(getattr(user_obj, 'id', '') or '')
                                cached = self._avatar_b64_cache.get(user_id, 'NOT_FOUND') if user_id else ''
                                if cached == 'NOT_FOUND':
                                    # Primeiro contato com este usuário: inicia download e aguarda até 1s
                                    task = asyncio.create_task(_get_avatar_b64(user_obj))
                                    try:
                                        await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
                                    except asyncio.TimeoutError:
                                        pass  # CDN demorou; task continua, próxima msg terá avatar
                                    avatar_html = self._avatar_b64_cache.get(user_id) or ''
                                elif cached is None:
                                    # Download já em andamento (outra msg deste usuário disparou antes)
                                    avatar_html = ''
                                else:
                                    # Cache hit: '', '<img...>' etc
                                    avatar_html = cached
                        except Exception:
                            pass

                        # Badges usando parsing manual corrigido para TikTokLive v6
                        badge_str = ''
                        try:
                            if user_obj:
                                badge_str = _get_badge_str(user_obj)
                        except Exception:
                            pass

                        # author_display: avatar + nome + badges (só se houver enriquecimento)
                        author_display = f"{avatar_html}{author}{badge_str}" if (avatar_html or badge_str) else None

                        print(f"[TikTok] {author}: {msg[:50]}...", flush=True)
                        _emit_if_new(author, msg, author_display=author_display)
                    except Exception as e:
                        print(f"⚠️ on_comment erro: {e}")

                # FIX #2: Capturar CommentsEvent — algumas mensagens vêm por este evento
                if CommentsEvent is not None:
                    @self.client.on(CommentsEvent)
                    async def on_comments(event: CommentsEvent):
                        """Captura mensagens que vêm pelo CommentsEvent em vez de CommentEvent."""
                        try:
                            raw = (getattr(event, 'comment', None)
                                   or getattr(event, 'message', None)
                                   or getattr(event, 'text', None)
                                   or getattr(event, 'content', None)
                                   or "")
                            if not raw:
                                return
                            msg = convert_emoticons(str(raw))

                            author = "Usuário"
                            ui = getattr(event, 'user', None) or getattr(event, 'user_info', None)
                            if ui:
                                author = (getattr(ui, 'nick_name', None)
                                          or getattr(ui, 'nickname', None)
                                          or getattr(ui, 'username', None)
                                          or "Usuário")

                            print(f"[TikTok-Comments] {author}: {msg[:50]}...", flush=True)
                            _emit_if_new(author, msg)
                        except Exception as e:
                            print(f"⚠️ on_comments erro: {e}")

                # FIX #3: Capturar BarrageEvent — mensagens do tipo "barrage" (comuns em lives populares)
                @self.client.on(BarrageEvent)
                async def on_barrage(event: BarrageEvent):
                    """Captura mensagens do tipo barrage (ignora eventos do sistema como animações)."""
                    try:
                        raw = (getattr(event, 'content', None)
                               or getattr(event, 'comment', None)
                               or getattr(event, 'message', None)
                               or getattr(event, 'text', None)
                               or "")
                        if not raw:
                            return

                        msg_str = str(raw)

                        # IGNORAR eventos do sistema (animações, notificações, etc.)
                        system_patterns = [
                            'join_animation', 'pm_mt_alp', 'Text(key=', 'default_pattern',
                            'TextFormat', 'color=', 'font_size', 'weight=',
                            'SystemMessage', 'Notification', 'WelcomeEvent'
                        ]
                        if any(p in msg_str for p in system_patterns):
                            return  # Ignorar mensagens do sistema

                        # Só processar se parecer uma mensagem de chat real
                        if len(msg_str) < 1 or msg_str.startswith('{') or msg_str.startswith('['):
                            return

                        msg = convert_emoticons(msg_str)

                        author = "Usuário"
                        ui = getattr(event, 'user', None) or getattr(event, 'user_info', None) or getattr(event, 'from_user', None)
                        if ui:
                            author = (getattr(ui, 'nick_name', None)
                                      or getattr(ui, 'nickname', None)
                                      or getattr(ui, 'username', None)
                                      or "Usuário")

                        print(f"[TikTok-Barrage] {author}: {msg[:50]}...", flush=True)
                        _emit_if_new(author, msg)
                    except Exception as e:
                        print(f"⚠️ on_barrage erro: {e}")

                # FIX #4: Capturar EcBarrageEvent — outro tipo de mensagem barrage
                if EcBarrageEvent is not None:
                    @self.client.on(EcBarrageEvent)
                    async def on_ec_barrage(event: EcBarrageEvent):
                        """Captura mensagens do tipo EcBarrage (ignora eventos do sistema)."""
                        try:
                            raw = (getattr(event, 'content', None)
                                   or getattr(event, 'comment', None)
                                   or getattr(event, 'message', None)
                                   or getattr(event, 'text', None)
                                   or "")
                            if not raw:
                                return

                            msg_str = str(raw)

                            # IGNORAR eventos do sistema
                            system_patterns = [
                                'join_animation', 'pm_mt_alp', 'Text(key=', 'default_pattern',
                                'TextFormat', 'color=', 'font_size', 'weight=',
                                'SystemMessage', 'Notification', 'WelcomeEvent'
                            ]
                            if any(p in msg_str for p in system_patterns):
                                return

                            # Só processar se parecer uma mensagem de chat real
                            if len(msg_str) < 1 or msg_str.startswith('{') or msg_str.startswith('['):
                                return

                            msg = convert_emoticons(msg_str)

                            author = "Usuário"
                            ui = getattr(event, 'user', None) or getattr(event, 'user_info', None)
                            if ui:
                                author = (getattr(ui, 'nick_name', None)
                                          or getattr(ui, 'nickname', None)
                                          or getattr(ui, 'username', None)
                                          or "Usuário")

                            print(f"[TikTok-EC] {author}: {msg[:50]}...", flush=True)
                            _emit_if_new(author, msg)
                        except Exception as e:
                            print(f"⚠️ on_ec_barrage erro: {e}")

                # DEBUG: Capturar TODOS os pacotes websocket para identificar mensagens perdidas
                @self.client.on(WebsocketResponseEvent)
                async def on_websocket_debug(event: WebsocketResponseEvent):
                    """Debug profundo: analisa TODOS os pacotes websocket procurando mensagens."""
                    try:
                        if hasattr(event, 'base_message') and event.base_message:
                            bm = event.base_message
                            method = getattr(bm, 'method', 'unknown')
                            payload = getattr(bm, 'payload', None)

                            # LOGAR TODOS os métodos (para ver o que está chegando)
                            if method:
                                print(f"[DEBUG-ALL] method={method}")

                            # Procurar por métodos relacionados a chat/comentários
                            if method and any(x in str(method).lower() for x in ['chat', 'comment', 'message', 'barrage', 'im', 'push']):
                                print(f"[DEBUG-CHAT] method={method}")

                                if payload:
                                    try:
                                        import re
                                        payload_str = payload.decode('utf-8', errors='ignore')
                                        matches = re.findall(r'[\x20-\x7E]{3,}', payload_str)
                                        potential_msgs = [m for m in matches if len(m) > 5 and ' ' in m][:5]
                                        if potential_msgs:
                                            print(f"[DEBUG-CHAT] Textos: {potential_msgs}")
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                # Handler para UnknownEvent - captura mensagens não reconhecidas pela lib
                @self.client.on(UnknownEvent)
                async def on_unknown(event: UnknownEvent):
                    """Captura eventos desconhecidos que podem ser mensagens perdidas."""
                    try:
                        # Verificar se tem conteúdo de texto potencial
                        has_text = False
                        text_content = ""

                        for attr in ['content', 'comment', 'message', 'text', 'body']:
                            try:
                                val = getattr(event, attr, None)
                                if val and isinstance(val, str) and len(val) > 0:
                                    has_text = True
                                    text_content = val
                                    break
                            except:
                                pass

                        if has_text:
                            print(f"[UNKNOWN] Mensagem em evento desconhecido: {text_content[:50]}...")
                    except Exception:
                        pass

                @self.client.on(EmoteChatEvent)
                async def on_emote_chat(event: EmoteChatEvent):
                    """Captura mensagens de usuários que usam emotes especiais (comum em inscritos)."""
                    try:
                        # EmoteChatEvent geralmente tem a mensagem no campo 'comment' ou 'message'
                        # mas muitas vezes o TikTok envia o texto como fallback
                        raw = getattr(event, 'comment', None) or getattr(event, 'message', None)
                        if not raw and hasattr(event, 'emote'):
                            # Se for só o emote, pegamos o ID/Nome dele
                            raw = f"[{getattr(event.emote, 'emote_id', 'emote')}]"
                        
                        if not raw: return
                        
                        msg = convert_emoticons(str(raw))
                        author = "Usuário"
                        ui = getattr(event, 'user', None) or getattr(event, 'user_info', None)
                        if ui:
                            author = (getattr(ui, 'nick_name', None) or getattr(ui, 'nickname', None) or getattr(ui, 'username', None) or "Usuário")
                        
                        _emit_if_new(author, msg)
                    except Exception as e:
                        print(f"⚠️ on_emote_chat erro: {e}")

                @self.client.on(SocialEvent)
                async def on_social(event: SocialEvent):
                    """Intercepta eventos sociais que aparecem como mensagens no chat nativo."""
                    try:
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        display_type = getattr(event, 'display_type', "")
                        if "follow" in display_type.lower():
                            msg = get_translation("follow_started", self.language)
                            self.message_received.emit(author, msg, "tiktok_event")
                        elif "share" in display_type.lower():
                            msg = get_translation("share_transmitted", self.language)
                            self.message_received.emit(author, msg, "tiktok_event")
                    except:
                        pass

                @self.client.on(GiftEvent)
                async def on_gift(event: GiftEvent):
                    """Exibe presentes do TikTok com ícone + nome + combo, igual ao app nativo."""
                    try:
                        if event.streaking:
                            return

                        author     = event.user.nickname
                        gift_name  = getattr(event.gift, 'name', None) or "Presente"
                        gift_count = getattr(event, 'repeat_count', 1)

                        # Busca o ícone no cache construído pelo fetch_gift_list
                        icon_html = await _get_gift_icon_html(gift_name)

                        # Fallback: tenta obter a URL diretamente do objeto gift caso o cache falhe
                        if not icon_html:
                            try:
                                gift_obj = event.gift
                                icon_url = (
                                    getattr(gift_obj, 'icon_url', None)
                                    or getattr(gift_obj, 'image_url', None)
                                    or getattr(gift_obj, 'cover', None)
                                )
                                if not icon_url:
                                    img_obj = getattr(gift_obj, 'image', None) or getattr(gift_obj, 'icon', None)
                                    if img_obj:
                                        url_list = getattr(img_obj, 'url_list', getattr(img_obj, 'm_urls', getattr(img_obj, 'urls', None)))
                                        if url_list and len(url_list) > 0:
                                            icon_url = url_list[0]
                                
                                if icon_url:
                                    # FIX #6: Headers obrigatórios — sem eles, TikTok retorna 403 para presentes novos
                                    gift_headers = {
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                        "Referer": "https://www.tiktok.com/"
                                    }
                                    async with httpx.AsyncClient(timeout=5.0, headers=gift_headers) as hc:
                                        resp = await hc.get(icon_url)
                                        if resp.status_code == 200 and resp.content:
                                            b64 = base64.b64encode(resp.content).decode()
                                            ct = resp.headers.get("content-type", "image/png")
                                            icon_html = f"<img src='data:{ct};base64,{b64}'>"
                                            self._gift_icon_cache[gift_name.lower()] = icon_url
                                            self._gift_b64_cache[gift_name.lower()] = icon_html
                                else:
                                    print(f"⚠️ [DEBUG] Gift '{gift_name}' sem URL de ícone encontrada.")
                            except Exception as e:
                                print(f"⚠️ [DEBUG] Erro no fallback do gift: {e}")

                        msg = get_translation("gift_sent_multiple", self.language, gift_name, icon_html, gift_count)
                        self.message_received.emit(author, msg, "tiktok_event")
                    except Exception as e:
                        print(f"⚠️ Erro ao processar presente: {e}")


                @self.client.on(FollowEvent)
                async def on_follow(event: FollowEvent):
                    try:
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        msg = get_translation("follow_started", self.language)
                        self.message_received.emit(author, msg, "tiktok_event")
                    except:
                        pass

                @self.client.on(ShareEvent)
                async def on_share(event: ShareEvent):
                    try:
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        msg = get_translation("share_transmitted", self.language)
                        self.message_received.emit(author, msg, "tiktok_event")
                    except:
                        pass

                @self.client.on(JoinEvent)
                async def on_join(event: JoinEvent):
                    """Handler para entrada de usuários (JoinEvent)"""
                    try:
                        # Extrai o nickname do usuário que entrou
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        # Emitimos o sinal que a UI usa para mostrar a notificação lateral
                        self.user_joined.emit(author, "tiktok")
                    except:
                        pass

                @self.client.on(ConnectEvent)
                async def on_connect(event: ConnectEvent):
                    self._connected_event.set()
                    self._reconnect_attempts = 0
                    self.status_changed.emit(True)
                    if not self._already_connected:
                        msg = get_translation("tiktok_connected", self.language, username=self.username)
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                        self._already_connected = True
                    
                    # Marca o timestamp de conexão para backup do uptime
                    self._start_ts = int(time.time())
                    
                    # Popula o cache de ícones
                    await _build_gift_cache()
                    
                    # FIX #4 + #5: Busca room_info para inicializar uptime E likes corretamente
                    try:
                        rid = getattr(self.client, 'room_id', None)
                        r_dict = await self.client.web.fetch_room_info(room_id=rid)
                        if isinstance(r_dict, dict):
                            # --- Uptime ---
                            if not self._create_time:
                                ct = r_dict.get('create_time') or r_dict.get('createTime') or r_dict.get('start_time')
                                if not ct:
                                    room = r_dict.get('room', r_dict.get('data', {}).get('room', {}))
                                    if isinstance(room, dict):
                                        ct = room.get('create_time') or room.get('createTime')
                                if ct:
                                    ts = int(ct)
                                    # Normaliza milissegundos → segundos
                                    if ts > 9_999_999_999:
                                        ts //= 1000
                                    self._create_time = ts
                                    self._room_info_fetched = True
                                    print(f"✅ Uptime sincronizado no ConnectEvent! (ts={ts})")

                            # --- FIX #4: Likes iniciais (total_like_count) ---
                            # Tenta extrair a contagem de likes atual da sala
                            # para não exibir 0 enquanto ninguém dá like ao vivo
                            if self._total_likes == 0:
                                try:
                                    # Campo mais comum na resposta da room_info
                                    likes_val = (
                                        r_dict.get('like_count')
                                        or r_dict.get('total_like_count')
                                        or r_dict.get('likeCount')
                                    )
                                    if not likes_val:
                                        room_obj = r_dict.get('room', r_dict.get('data', {}).get('room', {}))
                                        if isinstance(room_obj, dict):
                                            likes_val = (
                                                room_obj.get('like_count')
                                                or room_obj.get('total_like_count')
                                                or room_obj.get('likeCount')
                                            )
                                    if not likes_val:
                                        stats_obj = r_dict.get('stats', r_dict.get('data', {}).get('stats', {}))
                                        if isinstance(stats_obj, dict):
                                            likes_val = stats_obj.get('likeCount') or stats_obj.get('like_count') or stats_obj.get('total_like_count')
                                            
                                    if not likes_val:
                                        # Tentar do internal info
                                        internal_info = getattr(self.client, 'room_info', None)
                                        if internal_info:
                                            likes_val = getattr(internal_info, 'like_count', getattr(internal_info, 'likeCount', getattr(internal_info, 'total_like_count', None)))
                                            
                                    if likes_val:
                                        self._total_likes = int(likes_val)
                                        print(f"✅ Likes iniciais carregados: {self._total_likes}")
                                        # Emitir stats iniciais com likes corretos
                                        viewers = getattr(self.client, 'viewer_count', 0)
                                        uptime_s = max(0, int(time.time()) - (self._create_time or int(time.time())))
                                        self.stats_updated.emit(viewers, uptime_s, self._total_likes, getattr(self, '_total_views', 0))
                                except Exception as e_likes:
                                    print(f"⚠️ Não foi possível carregar likes iniciais: {e_likes}")
                    except Exception as e_room:
                        print(f"⚠️ Erro ao buscar room_info no connect: {e_room}")

                @self.client.on(DisconnectEvent)
                async def on_disconnect(event: DisconnectEvent):
                    if self.is_running:
                        self.status_changed.emit(False)
                        self._already_connected = False

                self._connected_event = asyncio.Event()
                self.message_received.emit(
                    get_translation("tiktok_connect_attempt", self.language),
                    get_translation("tiktok_attempting", self.language, username=self.username),
                    "system"
                )
                self._loop_task = await self.client.start()
                try:
                    await asyncio.wait_for(self._connected_event.wait(), timeout=20.0)
                except asyncio.TimeoutError:
                    if self.is_running:
                        self.status_changed.emit(False)
                        self.message_received.emit(
                            get_translation("tiktok_connect_attempt", self.language),
                            get_translation("tiktok_error", self.language, error="Timeout connecting to TikTok."),
                            "system"
                        )
                    await self.client.disconnect()
                    return
                try:
                    await self._loop_task
                except asyncio.CancelledError:
                    pass

                if self.is_running:
                    self.status_changed.emit(False)
                    self.message_received.emit(
                        get_translation("tiktok_connect_attempt", self.language),
                        get_translation("tiktok_disconnected", self.language),
                        "system"
                    )

            except Exception as e:
                error_str = str(e).lower()
                if self.is_running:
                    with open('tiktok_exe_error.log', 'a', encoding='utf-8') as f:
                        f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                        f.write(traceback.format_exc())
                        f.write("\n")
                if "429" in error_str or "rate_limit" in error_str or "too many connections" in error_str:
                    self._rate_limited = True
                    if self.is_running:
                        self.status_changed.emit(False)
                        msg = get_translation("tiktok_rate_limited", self.language, username=self.username, error=str(e)[:100])
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                    self.is_running = False
                elif "offline" in error_str or "not found" in error_str or "room_id" in error_str or "has ended" in error_str or "is over" in error_str:
                    if self.is_running:
                        self.status_changed.emit(False)
                        msg = get_translation("tiktok_offline", self.language, username=self.username)
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                    self.is_running = False
                elif self.is_running:
                    self.status_changed.emit(False)
                    msg = get_translation("tiktok_error", self.language, error=str(e))
                    self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
            finally:
                self.client = None

        async def run_tiktok():
            while self.is_running:
                await run_tiktok_once()
                if self.is_running and not self._rate_limited:
                    self._reconnect_attempts += 1
                    if self._reconnect_attempts > 5:
                        self.is_running = False
                        self.status_changed.emit(False)
                        msg = "Limite de 5 tentativas de reconexão atingido. Parando para evitar bloqueio."
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                        break
                    await asyncio.sleep(5)

        asyncio.run_coroutine_threadsafe(run_tiktok(), self.loop)

    def stop(self):
        self.is_running = False
        if getattr(self, 'loop', None):
            if getattr(self, '_loop_task', None) and not self._loop_task.done():
                self.loop.call_soon_threadsafe(self._loop_task.cancel)
        
        if getattr(self, 'client', None) and self.loop:
            try:
                if asyncio.iscoroutinefunction(self.client.disconnect):
                    asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
                else:
                    # Pode ser que client.disconnect não seja corotina em algumas versões do TikTokLive
                    self.client.disconnect()
            except Exception as e:
                print(f"⚠️ Erro ao parar TikTok: {e}")

    def is_rate_limited(self):
        return self._rate_limited

    def reset_rate_limit(self):
        self._rate_limited = False
