from urllib.parse import quote, urlencode

from TikTokLive import TikTokLiveClient
import TikTokLive.events as TikTokEvents
from TikTokLive.events import (
    CommentEvent, ConnectEvent, DisconnectEvent, GiftEvent, FollowEvent,
    ShareEvent, RoomUserSeqEvent, LikeEvent, JoinEvent, EmoteChatEvent,
    SocialEvent, UnknownEvent, BarrageEvent,
    WebsocketResponseEvent
)

# Novos eventos TikTok (fan club, super fan, conquistas) — carregados com getattr
# para manter compatibilidade com versões mais antigas da lib
SubNotifyEvent = getattr(TikTokEvents, "SubNotifyEvent", None)
SuperFanEvent = getattr(TikTokEvents, "SuperFanEvent", None)
SuperFanJoinEvent = getattr(TikTokEvents, "SuperFanJoinEvent", None)
SuperFanBoxEvent = getattr(TikTokEvents, "SuperFanBoxEvent", None)
RoomNotifyEvent = getattr(TikTokEvents, "RoomNotifyEvent", None)
HourlyRankRewardEvent = getattr(TikTokEvents, "HourlyRankRewardEvent", None)

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
from utils.avatar_utils import make_circular_base64_png
from TikTokLive.proto.custom_proto import ExtendedUser
import asyncio
import base64
import httpx
import time
import os
import re
import traceback
import logging
class _IgnoreWebcastLinkLayerFilter(logging.Filter):
    def filter(self, record):
        try:
            return "WebcastLinkLayerMessage" not in record.getMessage()
        except Exception:
            return True

logging.getLogger("TikTokLive").addFilter(_IgnoreWebcastLinkLayerFilter())
logging.getLogger("TikTokLive.client").addFilter(_IgnoreWebcastLinkLayerFilter())



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
        self._online_viewers_map = {} # {user_id: viewer_dict}

    def _record_online_viewer(self, user, score=None, rank=None):
        """Registra/atualiza espectador online em tempo real."""
        if not user:
            return
        user_id = str(getattr(user, 'id', '') or '')
        nickname = str(getattr(user, 'nickname', '') or getattr(user, 'nick_name', '') or getattr(user, 'display_id', '') or 'Usuário')
        display_id = str(getattr(user, 'display_id', '') or getattr(user, 'unique_id', '') or '')

        if not hasattr(self, '_online_viewers_map'):
            self._online_viewers_map = {}

        # Coleta avatar URLs
        avatar_urls = []
        for av_field in ['avatar_thumb', 'avatar_medium', 'avatar_large', 'avatar_168x168', 'avatar_300x300', 'avatar_jpg']:
            av_obj = getattr(user, av_field, None)
            if av_obj:
                u_list = getattr(av_obj, 'url_list', None) or getattr(av_obj, 'urls_list', None) or []
                if isinstance(u_list, list):
                    for u in u_list:
                        if u and u not in avatar_urls:
                            avatar_urls.append(u)
                elif isinstance(av_obj, str) and av_obj.startswith('http'):
                    if av_obj not in avatar_urls:
                        avatar_urls.append(av_obj)

        avatar_url = avatar_urls[0] if avatar_urls else ''

        key = user_id if user_id else (display_id or nickname)
        existing = self._online_viewers_map.get(key, {})
        current_score = score if score is not None else existing.get('score', 0)
        current_rank = rank if rank is not None else existing.get('rank', 999)

        self._online_viewers_map[key] = {
            'user_id': user_id,
            'nickname': nickname,
            'display_id': display_id,
            'score': current_score,
            'rank': current_rank,
            'avatar_url': avatar_url or existing.get('avatar_url', ''),
            'avatar_urls': avatar_urls or existing.get('avatar_urls', []),
            'last_active': time.time()
        }

    def _emit_realtime_viewers(self, total_online=0):
        """Ordena e emite a lista de espectadores online atualizada na hora."""
        if not hasattr(self, '_online_viewers_map') or not self._online_viewers_map:
            return

        now = time.time()
        # Mantém quem tem pontuação ou interagiu nos últimos 15 minutos
        self._online_viewers_map = {
            k: v for k, v in self._online_viewers_map.items()
            if v.get('score', 0) > 0 or (now - v.get('last_active', 0) < 900)
        }

        sorted_viewers = sorted(
            self._online_viewers_map.values(),
            key=lambda v: (
                -v.get('score', 0),
                v.get('rank', 999) if v.get('rank', 999) > 0 else 999,
                -v.get('last_active', 0)
            )
        )

        final_list = []
        for i, v in enumerate(sorted_viewers[:50]):
            v_copy = dict(v)
            v_copy['rank'] = i + 1
            final_list.append(v_copy)

        self.viewers_list_updated.emit(final_list)

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
                        'open_timeout': 30.0,
                        'close_timeout': 10.0,
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
                        for av_field in ['avatar_thumb', 'avatar_medium', 'avatar_large', 'avatar_168x168', 'avatar_300x300', 'avatar_jpg']:
                            av_obj = getattr(user_obj, av_field, None)
                            if av_obj:
                                if isinstance(av_obj, dict):
                                    u_list = av_obj.get('url_list') or av_obj.get('urls_list') or []
                                    if u_list:
                                        avatar_url = u_list[0]
                                        break
                                elif isinstance(av_obj, list):
                                    for u in av_obj:
                                        if u and isinstance(u, str) and u.startswith('http'):
                                            avatar_url = u
                                            break
                                    if avatar_url:
                                        break
                                elif isinstance(av_obj, str) and av_obj.startswith('http'):
                                    avatar_url = av_obj
                                    break
                                else:
                                    u_list = getattr(av_obj, 'url_list', None) or getattr(av_obj, 'urls_list', None) or []
                                    if u_list and len(u_list) > 0:
                                        avatar_url = u_list[0]
                                        break
                        if not avatar_url:
                            self._avatar_b64_cache[user_id] = ''
                            return ''
                        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tiktok.com/"}
                        async with httpx.AsyncClient(timeout=5.0, headers=headers) as hc:
                            resp = await hc.get(avatar_url)
                            if resp.status_code == 200 and resp.content:
                                b64_png = make_circular_base64_png(resp.content, size=22, border_color="rgba(255, 255, 255, 120)", border_width=1.0)
                                if b64_png:
                                    tag = f"<img src='data:image/png;base64,{b64_png}' width='22' height='22' style='vertical-align:middle;margin-right:4px;'>"
                                else:
                                    raw_b64 = base64.b64encode(resp.content).decode()
                                    ct = resp.headers.get("content-type", "image/jpeg")
                                    tag = f"<img src='data:{ct};base64,{raw_b64}' width='22' height='22' style='vertical-align:middle;margin-right:4px;'>"
                                
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
                    """Retorna HTML com badges oficiais do TikTok (CDN original) ou fallback SVG. Nunca levanta exceção."""
                    try:
                        from utils.badge_manager import badge_manager
                        return badge_manager.get_tiktok_badges_html(user_obj)
                    except Exception:
                        return ''

                def _get_badges_tuple(user_obj) -> tuple[str, str]:
                    """Retorna (prefix_html, suffix_html) com badges oficiais."""
                    try:
                        from utils.badge_manager import badge_manager
                        return badge_manager.get_tiktok_badges_tuple(user_obj)
                    except Exception:
                        return ('', '')

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
                        
                        # 1. Primeiro converte os emoticons de texto (ex: [laugh], KEKW) no texto puro
                        msg = convert_emoticons(raw)
                        
                        # 2. 🔥 Emojis / Conquistas Customizados do TikTok
                        if getattr(event, 'emotes', None):
                            try:
                                emotes_to_process = []
                                for e in event.emotes:
                                    emote_obj = getattr(e, 'emote', None)
                                    idx = getattr(e, 'index', -1)
                                    if emote_obj:
                                        emotes_to_process.append((idx, emote_obj))
                                
                                if emotes_to_process:
                                    tags_by_idx = {}
                                    append_tags = []
                                    
                                    for idx, emote_obj in emotes_to_process:
                                        img_obj = getattr(emote_obj, 'image', None)
                                        if not img_obj:
                                            continue
                                        urls = getattr(img_obj, 'url_list', [])
                                        if not urls:
                                            continue
                                        
                                        img_url = str(urls[0])
                                        emote_id = str(getattr(emote_obj, 'emote_id', 'unknown'))
                                        
                                        # Roda de forma async (via thread do executor) para não bloquear o loop do TikTok
                                        local_url = await asyncio.get_event_loop().run_in_executor(
                                            None, get_emote_url, img_url, f"ttk_{emote_id}"
                                        )
                                        
                                        if local_url:
                                            img_tag = f"<img src='{local_url}' width='22' height='22' style='vertical-align: middle; margin: 0 1px;'>"
                                            if idx is None or idx < 0 or idx >= len(msg):
                                                append_tags.append(img_tag)
                                            else:
                                                if idx not in tags_by_idx:
                                                    tags_by_idx[idx] = []
                                                tags_by_idx[idx].append(img_tag)
                                    
                                    # Inserir no texto do fim para o começo do texto original para manter posições válidas
                                    sorted_indices = sorted(tags_by_idx.keys(), reverse=True)
                                    for idx in sorted_indices:
                                        tags_str = " ".join(tags_by_idx[idx])
                                        # Se houver placeholder [nome] na posição indicada, substitui até o ']'
                                        if idx < len(msg) and msg[idx] == '[':
                                            end_bracket = msg.find(']', idx)
                                            if end_bracket != -1:
                                                msg = msg[:idx] + tags_str + msg[end_bracket + 1:]
                                                continue
                                        # Caso contrário, insere com espaçamento limpo
                                        p_space = " " if (idx > 0 and msg[idx-1] != ' ') else ""
                                        s_space = " " if (idx < len(msg) and msg[idx] != ' ') else ""
                                        msg = msg[:idx] + p_space + tags_str + s_space + msg[idx:]
                                    
                                    if append_tags:
                                        msg = msg.strip() + " " + " ".join(append_tags)
                                    
                                    # Limpa espaços extras
                                    msg = re.sub(r' +', ' ', msg).strip()
                            except Exception as em_e:
                                print(f"⚠️ Erro ao processar emotes customizados do TikTok: {em_e}")

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

                        # Badges usando parsing completo de níveis e ícones oficiais
                        prefix_badges = ''
                        suffix_badges = ''
                        try:
                            if user_obj:
                                prefix_badges, suffix_badges = _get_badges_tuple(user_obj)
                        except Exception:
                            pass

                        # author_display: avatar + badges antes (nível, fã-clube) + nome + badges depois (top gifter #1)
                        author_display = f"{avatar_html}{prefix_badges}{author}{suffix_badges}" if (avatar_html or prefix_badges or suffix_badges) else None

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
                            'SystemMessage', 'Notification', 'WelcomeEvent',
                            # Padrões de superfã e fã-clube — tratados por handlers dedicados
                            'ttlive_superfan', 'superfan', 'fan_club', 'fans_club',
                            'subscribe_notify', 'sub_notify',
                        ]
                        if any(p.lower() in msg_str.lower() for p in system_patterns):
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
                                'SystemMessage', 'Notification', 'WelcomeEvent',
                                # Padrões de superfã e fã-clube — tratados por handlers dedicados
                                'ttlive_superfan', 'superfan', 'fan_club', 'fans_club',
                                'subscribe_notify', 'sub_notify',
                            ]
                            if any(p.lower() in msg_str.lower() for p in system_patterns):
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
                        raw = getattr(event, 'comment', None) or getattr(event, 'message', None)
                        emote_obj = getattr(event, 'emote', None)
                        
                        if not raw and emote_obj:
                            img_obj = getattr(emote_obj, 'image', None)
                            urls = getattr(img_obj, 'url_list', []) if img_obj else []
                            if urls:
                                img_url = str(urls[0])
                                emote_id = str(getattr(emote_obj, 'emote_id', 'unknown'))
                                local_url = await asyncio.get_event_loop().run_in_executor(
                                    None, get_emote_url, img_url, f"ttk_{emote_id}"
                                )
                                if local_url:
                                    raw = f"<img src='{local_url}' width='22' height='22' style='vertical-align: middle; margin: 0 1px;'>"
                            if not raw:
                                raw = f"[{getattr(emote_obj, 'emote_id', 'emote')}]"
                        
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
                    """Exibe presentes do TikTok com avatar + nome + badges + ícone do presente."""
                    try:
                        if event.streaking:
                            return

                        user_obj = getattr(event, 'user', None)
                        author = "Usuário"
                        if user_obj:
                            author = getattr(user_obj, 'nickname', getattr(user_obj, 'nick_name', "Usuário"))
                        gift_name  = getattr(event.gift, 'name', None) or "Presente"
                        gift_count = getattr(event, 'repeat_count', 1) or getattr(event.gift, 'repeat_count', 1) or 1

                        # Avatar do usuário
                        avatar_html = ''
                        if user_obj:
                            avatar_html = await _get_avatar_b64(user_obj)

                        # Badges
                        prefix_badges = ''
                        suffix_badges = ''
                        if user_obj:
                            try:
                                prefix_badges, suffix_badges = _get_badges_tuple(user_obj)
                            except:
                                pass

                        author_display = f"{avatar_html}{prefix_badges}{author}{suffix_badges}" if (avatar_html or prefix_badges or suffix_badges) else author

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
                            except Exception as e:
                                pass

                        msg = get_translation("gift_sent_multiple", self.language, gift_name, icon_html, gift_count)
                        self.message_received.emit(author_display, msg, "tiktok_event")

                    except Exception as e:
                        print(f"⚠️ Erro ao processar presente: {e}")


                @self.client.on(FollowEvent)
                async def on_follow(event: FollowEvent):
                    try:
                        user_obj = getattr(event, 'user', None)
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        avatar_html = ''
                        if user_obj:
                            avatar_html = await _get_avatar_b64(user_obj)
                        author_display = f"{avatar_html}{author}" if avatar_html else author
                        msg = get_translation("follow_started", self.language)
                        self.message_received.emit(author_display, msg, "tiktok_event")
                    except:
                        pass

                @self.client.on(ShareEvent)
                async def on_share(event: ShareEvent):
                    try:
                        user_obj = getattr(event, 'user', None)
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        avatar_html = ''
                        if user_obj:
                            avatar_html = await _get_avatar_b64(user_obj)
                        author_display = f"{avatar_html}{author}" if avatar_html else author
                        msg = get_translation("share_transmitted", self.language)
                        self.message_received.emit(author_display, msg, "tiktok_event")
                    except:
                        pass

                # ── Novos eventos: Fã-clube, Super Fã, Notificações de sala ─────────────

                if SubNotifyEvent is not None:
                    @self.client.on(SubNotifyEvent)
                    async def on_sub_notify(event: SubNotifyEvent):
                        """Fã-clube: entrada e milestones de meses (SubNotifyEvent)."""
                        try:
                            user_obj = getattr(event, 'user', None)
                            author = "Usuário"
                            if user_obj:
                                author = (getattr(user_obj, 'nickname', None)
                                          or getattr(user_obj, 'nick_name', None)
                                          or "Usuário")

                            # Número de meses no fã-clube
                            sub_month = getattr(event, 'sub_month', 0) or 0

                            # Avatar
                            avatar_html = ''
                            if user_obj:
                                avatar_html = await _get_avatar_b64(user_obj)
                            author_display = f"{avatar_html}{author}" if avatar_html else author

                            # Ícone de fã-clube local
                            fan_icon_path = resource_path('assets/tiktok_fan.svg').replace('\\', '/')
                            fan_icon = (f"<img src='file:///{fan_icon_path}' "
                                        f"width='18' height='18' "
                                        f"style='vertical-align:middle;margin-right:3px;'>")

                            if sub_month and int(sub_month) > 0:
                                n = int(sub_month)
                                # Singular/plural por idioma
                                if self.language == "en":
                                    unit = "month" if n == 1 else "months"
                                else:  # pt-br e outros
                                    unit = "mês" if n == 1 else "meses"
                                time_str = f"{n} {unit}"
                                msg = get_translation("fan_club_months", self.language, fan_icon, time_str)
                            else:
                                msg = get_translation("fan_club_joined", self.language, fan_icon)

                            self.message_received.emit(author_display, msg, "tiktok_event")
                        except Exception as e:
                            print(f"⚠️ on_sub_notify erro: {e}")

                if SuperFanEvent is not None:
                    @self.client.on(SuperFanEvent)
                    async def on_super_fan(event: SuperFanEvent):
                        """Usuário se torna super fã (SuperFanEvent)."""
                        try:
                            user_obj = getattr(event, 'user', None)
                            author = "Usuário"
                            if user_obj:
                                author = (getattr(user_obj, 'nickname', None)
                                          or getattr(user_obj, 'nick_name', None)
                                          or "Usuário")

                            avatar_html = ''
                            if user_obj:
                                avatar_html = await _get_avatar_b64(user_obj)
                            author_display = f"{avatar_html}{author}" if avatar_html else author

                            fan_icon_path = resource_path('assets/tiktok_fan.svg').replace('\\', '/')
                            fan_icon = (f"<img src='file:///{fan_icon_path}' "
                                        f"width='18' height='18' "
                                        f"style='vertical-align:middle;margin-right:3px;'>")
                            msg = get_translation("super_fan_became", self.language, fan_icon)
                            self.message_received.emit(author_display, msg, "tiktok_event")
                        except Exception as e:
                            print(f"⚠️ on_super_fan erro: {e}")

                if SuperFanJoinEvent is not None:
                    @self.client.on(SuperFanJoinEvent)
                    async def on_super_fan_join(event: SuperFanJoinEvent):
                        """Super fã entrou na live (SuperFanJoinEvent)."""
                        try:
                            user_obj = getattr(event, 'user', None)
                            author = "Usuário"
                            if user_obj:
                                author = (getattr(user_obj, 'nickname', None)
                                          or getattr(user_obj, 'nick_name', None)
                                          or "Usuário")

                            avatar_html = ''
                            if user_obj:
                                avatar_html = await _get_avatar_b64(user_obj)
                            author_display = f"{avatar_html}{author}" if avatar_html else author

                            fan_icon_path = resource_path('assets/tiktok_fan.svg').replace('\\', '/')
                            fan_icon = (f"<img src='file:///{fan_icon_path}' "
                                        f"width='18' height='18' "
                                        f"style='vertical-align:middle;margin-right:3px;'>")
                            msg = get_translation("super_fan_joined", self.language, fan_icon)
                            self.message_received.emit(author_display, msg, "tiktok_event")
                        except Exception as e:
                            print(f"⚠️ on_super_fan_join erro: {e}")

                if RoomNotifyEvent is not None:
                    @self.client.on(RoomNotifyEvent)
                    async def on_room_notify(event: RoomNotifyEvent):
                        """Notificações de sala: conquistas, minutos assistidos, etc. (RoomNotifyEvent)."""
                        try:
                            user_obj = getattr(event, 'user', None)
                            author = "Usuário"
                            if user_obj:
                                author = (getattr(user_obj, 'nickname', None)
                                          or getattr(user_obj, 'nick_name', None)
                                          or "Usuário")

                            # O conteúdo vem no campo 'content' como texto plano
                            content = str(getattr(event, 'content', '') or '').strip()
                            if not content:
                                return  # Sem conteúdo, ignora

                            # Filtra HTML cru e padrões proto que não são mensagens reais
                            skip_patterns = ['<img', 'Text(key=', 'TextFormat', 'display_type', 'schema=']
                            if any(p in content for p in skip_patterns):
                                return

                            avatar_html = ''
                            if user_obj:
                                avatar_html = await _get_avatar_b64(user_obj)
                            author_display = f"{avatar_html}{author}" if avatar_html else author

                            # Ícone genérico de notificação (estrela/conquista)
                            star_path = resource_path('assets/tiktok_fan.svg').replace('\\', '/')
                            star_icon = (f"<img src='file:///{star_path}' "
                                         f"width='16' height='16' "
                                         f"style='vertical-align:middle;margin-right:3px;'>")

                            msg = f"{star_icon} {content}"
                            self.message_received.emit(author_display, msg, "tiktok_event")
                        except Exception as e:
                            print(f"⚠️ on_room_notify erro: {e}")

                @self.client.on(LikeEvent)
                async def on_like(event: LikeEvent):
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
                    
                    # Dispara busca de presentes e detalhes da sala em background sem travar o on_connect
                    asyncio.create_task(_build_gift_cache())
                    asyncio.create_task(_init_room_details())

                async def _init_room_details():
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
                                    if ts > 9_999_999_999:
                                        ts //= 1000
                                    self._create_time = ts
                                    self._room_info_fetched = True
                                    print(f"✅ Uptime sincronizado no ConnectEvent! (ts={ts})")

                            # --- Likes iniciais ---
                            if self._total_likes == 0:
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
                                if likes_val:
                                    self._total_likes = int(likes_val)
                                    print(f"✅ Likes iniciais carregados: {self._total_likes}")
                                    viewers = getattr(self.client, 'viewer_count', 0)
                                    uptime_s = max(0, int(time.time()) - (self._create_time or int(time.time())))
                                    self.stats_updated.emit(viewers, uptime_s, self._total_likes, getattr(self, '_total_views', 0))

                            # Extrai IDs do streamer para sincronização contínua de espectadores
                            owner = r_dict.get('owner', {}) if isinstance(r_dict, dict) else {}
                            self._anchor_id = owner.get('id', '') or owner.get('id_str', '')
                            self._sec_anchor_id = owner.get('sec_uid', '')
                            if self._anchor_id:
                                self._sync_task = asyncio.create_task(_sync_online_audience_loop())
                    except Exception as e_room:
                        print(f"⚠️ Erro ao buscar room_info no connect: {e_room}")

                async def _sync_online_audience_loop():
                    """Busca a lista completa de todos os espectadores online via webcast API.

                    Requer autenticação TikTok (sessionid). Se não houver sessionid,
                    o loop encerra imediatamente sem fazer nenhuma requisição ao TikTok,
                    evitando erros 401/403/429.
                    """
                    # Early-exit: sem sessionid, a API /online_audience/ requer login.
                    # Não fazemos NENHUMA requisição para não arriscar 429 ou banimento.
                    if not session_id:
                        print(
                            "ℹ️ [Espectadores] Sem login TikTok — aba de usuários online desativada. "
                            "Faça login em Configurações → TikTok para ativar.",
                            flush=True
                        )
                        return  # Para completamente — sem loop, sem requisições

                    while self.is_running and self._already_connected:
                        try:
                            rid = getattr(self.client, 'room_id', None)
                            if rid and getattr(self, '_anchor_id', None):
                                url = f"https://webcast.tiktok.com/webcast/ranklist/online_audience/?aid=1988&device_platform=web_pc&room_id={rid}&anchor_id={self._anchor_id}&sec_anchor_id={getattr(self, '_sec_anchor_id', '')}"
                                headers = {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                    "Referer": f"https://www.tiktok.com/@{self.username}/live"
                                }
                                cookies = {'sessionid': session_id}
                                try:
                                    async with httpx.AsyncClient(headers=headers, cookies=cookies, timeout=6.0) as hc:
                                        resp = await hc.get(url)

                                        # Sem autenticação: TikTok retorna 401, 403 ou 200 com dados vazios
                                        if resp.status_code in (401, 403):
                                            if not _auth_warned:
                                                print(
                                                    "ℹ️ [Espectadores] A aba de usuários online requer login TikTok. "
                                                    "Faça login em Configurações → TikTok para ver a lista completa.",
                                                    flush=True
                                                )
                                                _auth_warned = True
                                            await asyncio.sleep(30.0)  # Espera mais antes de tentar de novo
                                            continue

                                        if resp.status_code == 200:
                                            try:
                                                data = resp.json()
                                            except Exception:
                                                await asyncio.sleep(4.0)
                                                continue

                                            d = data.get('data', {})
                                            ranks = d.get('ranks', [])

                                            # Resposta vazia = não autenticado ou live sem audiência listada
                                            if not ranks:
                                                if not _auth_warned and not session_id:
                                                    print(
                                                        "ℹ️ [Espectadores] Lista vazia — faça login no TikTok em Configurações "
                                                        "para ver os espectadores online.",
                                                        flush=True
                                                    )
                                                    _auth_warned = True
                                                await asyncio.sleep(4.0)
                                                continue

                                            # Reseta o aviso caso tenha conseguido dados
                                            _auth_warned = False
                                            viewers_list = []
                                            total_in_room = d.get('total', 0)

                                            for idx, rk in enumerate(ranks):
                                                user = rk.get('user', {})
                                                if not user:
                                                    continue
                                                user_id = str(user.get('id', '') or '')
                                                nickname = str(user.get('nickname', '') or user.get('nick_name', '') or user.get('display_id', '') or 'Usuário')
                                                display_id = str(user.get('display_id', '') or user.get('unique_id', '') or '')
                                                score = rk.get('score', 0)
                                                rank_num = idx + 1

                                                # Coleta URLs de avatar
                                                avatar_urls = []
                                                for av_field in ['avatar_thumb', 'avatar_medium', 'avatar_large', 'avatar_168x168', 'avatar_300x300', 'avatar_jpg']:
                                                    av_obj = user.get(av_field)
                                                    if av_obj:
                                                        if isinstance(av_obj, dict):
                                                            u_list = av_obj.get('url_list') or av_obj.get('urls_list') or []
                                                            for u in u_list:
                                                                if u and u not in avatar_urls:
                                                                    avatar_urls.append(u)
                                                        elif isinstance(av_obj, list):
                                                            for u in av_obj:
                                                                if u and isinstance(u, str) and u.startswith('http') and u not in avatar_urls:
                                                                    avatar_urls.append(u)
                                                        elif isinstance(av_obj, str) and av_obj.startswith('http'):
                                                            if av_obj not in avatar_urls:
                                                                avatar_urls.append(av_obj)

                                                avatar_url = avatar_urls[0] if avatar_urls else ''

                                                viewers_list.append({
                                                    'rank': rank_num,
                                                    'user_id': user_id,
                                                    'nickname': nickname,
                                                    'display_id': display_id,
                                                    'score': score,
                                                    'avatar_url': avatar_url,
                                                    'avatar_urls': avatar_urls,
                                                    'total_online': total_in_room
                                                })

                                            if viewers_list and self.is_running and self._already_connected:
                                                self.viewers_list_updated.emit(viewers_list)

                                except httpx.TimeoutException:
                                    pass  # Timeout de rede — tenta de novo no próximo ciclo
                                except httpx.RequestError:
                                    pass  # Erro de conexão — tenta de novo no próximo ciclo
                        except Exception:
                            pass
                        await asyncio.sleep(4.0)

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
                    await asyncio.wait_for(self._connected_event.wait(), timeout=35.0)
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
                elif ("not capable" in error_str
                      or "never gone live" in error_str
                      or "not going live" in error_str
                      or "does not exist" in error_str
                      or "not found" in error_str
                      or "userunavailable" in error_str):
                    # Usuário não existe ou nunca foi ao vivo — não adianta reconectar
                    if self.is_running:
                        self.status_changed.emit(False)
                        msg = get_translation("tiktok_not_found", self.language, username=self.username)
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                    self.is_running = False
                elif ("offline" in error_str
                      or "room_id" in error_str
                      or "has ended" in error_str
                      or "is over" in error_str
                      or "live has ended" in error_str):
                    # Canal existe mas está offline no momento
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
        self._already_connected = False
        if hasattr(self, '_online_viewers_map'):
            self._online_viewers_map.clear()

        if getattr(self, '_sync_task', None) and not self._sync_task.done():
            if getattr(self, 'loop', None):
                self.loop.call_soon_threadsafe(self._sync_task.cancel)

        if getattr(self, 'loop', None):
            if getattr(self, '_loop_task', None) and not self._loop_task.done():
                self.loop.call_soon_threadsafe(self._loop_task.cancel)
        
        if getattr(self, 'client', None) and self.loop:
            try:
                if asyncio.iscoroutinefunction(self.client.disconnect):
                    asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
                else:
                    self.client.disconnect()
            except Exception as e:
                print(f"⚠️ Erro ao parar TikTok: {e}")

    def is_rate_limited(self):
        return self._rate_limited

    def reset_rate_limit(self):
        self._rate_limited = False
