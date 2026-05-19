from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent, ConnectEvent, DisconnectEvent, GiftEvent, FollowEvent,
    ShareEvent, RoomUserSeqEvent, LikeEvent, JoinEvent, EmoteChatEvent,
    SocialEvent, CommentsEvent, UnknownEvent, BarrageEvent, EcBarrageEvent,
    WebsocketResponseEvent
)
from .base_handler import BaseChatHandler
from utils.emoticons import convert_emoticons
from utils.translations import get_translation
import asyncio
import base64
import httpx
import time


class TikTokHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "tiktok"
        self.client = None
        self.loop = None
        self._msg_history = []
        self._rate_limited = False

    def start_with_loop(self, loop):
        self.loop = loop
        self.is_running = True
        async def run_tiktok():
            try:
                # Revertendo para o formato estável e adicionando debug da lista de presentes
                self.client = TikTokLiveClient(unique_id=self.username)

                self._already_connected = False
                self._create_time = None
                self._total_likes = 0
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

                async def _sync_uptime_background():
                    """Busca uptime em background sem bloquear o event loop de mensagens."""
                    try:
                        import re
                        url = f"https://www.tiktok.com/@{self.username}/live"
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                        async with httpx.AsyncClient(timeout=10.0, headers=headers) as hc:
                            resp = await hc.get(url)
                            if resp.status_code == 200:
                                m = re.search(r'\"(?:startTime|createTime|create_time)\":(\d{10})', resp.text)
                                if m:
                                    self._create_time = int(m.group(1))
                                    self._room_info_fetched = True
                                    print(f"✅ Uptime sincronizado via HTML Scraping!")
                                    return
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
                                if v > 2000000000: v //= 1000
                                self._create_time = v
                                self._room_info_fetched = True
                                print(f"✅ Uptime sincronizado via Web API!")
                    except:
                        pass

                @self.client.on(LikeEvent)
                async def on_like(event: LikeEvent):
                    self._total_likes = getattr(event, 'total', getattr(event, 'total_likes', self._total_likes))
                    uptime_seconds = int(time.time()) - (self._create_time or int(time.time()))
                    viewers = getattr(self.client, 'viewer_count', 0)
                    self.stats_updated.emit(viewers, max(0, uptime_seconds), self._total_likes)

                @self.client.on(RoomUserSeqEvent)
                async def on_user_seq(event: RoomUserSeqEvent):
                    viewers = getattr(event, 'total', getattr(event, 'viewer_count', getattr(event, 'm_total', 0)))

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
                    self.stats_updated.emit(viewers, uptime_seconds, self._total_likes)

                # FIX #1: on_comment blindado — nenhuma mensagem se perde silenciosamente
                @self.client.on(CommentEvent)
                async def on_comment(event: CommentEvent):
                    try:
                        # Fallback de campos: comment → message → text (compatibilidade de versões)
                        raw = (getattr(event, 'comment', None)
                               or getattr(event, 'message', None)
                               or getattr(event, 'text', None)
                               or "")
                        if not raw:
                            return  # Mensagem genuinamente vazia
                        msg = convert_emoticons(str(raw))

                        # Fallback de usuário: user_info → user (compatibilidade de versões)
                        author = "Usuário"
                        try:
                            ui = getattr(event, 'user_info', None) or getattr(event, 'user', None)
                            if ui:
                                author = (getattr(ui, 'nick_name', None)
                                          or getattr(ui, 'nickname', None)
                                          or getattr(ui, 'username', None)
                                          or "Usuário")
                        except:
                            pass

                        print(f"[TikTok] {author}: {msg[:50]}...", flush=True)
                        self.message_received.emit(author, msg, "tiktok")
                    except Exception as e:
                        print(f"⚠️ on_comment erro: {e}")

                # FIX #2: Capturar CommentsEvent — algumas mensagens vêm por este evento
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
                        self.message_received.emit(author, msg, "tiktok")
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
                        self.message_received.emit(author, msg, "tiktok")
                    except Exception as e:
                        print(f"⚠️ on_barrage erro: {e}")

                # FIX #4: Capturar EcBarrageEvent — outro tipo de mensagem barrage
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
                        self.message_received.emit(author, msg, "tiktok")
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
                        
                        self.message_received.emit(author, msg, "tiktok")
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
                            self.message_received.emit(author, msg, "tiktok")
                        elif "share" in display_type.lower():
                            msg = get_translation("share_transmitted", self.language)
                            self.message_received.emit(author, msg, "tiktok")
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
                                    async with httpx.AsyncClient(timeout=5.0) as hc:
                                        resp = await hc.get(icon_url)
                                        if resp.status_code == 200 and resp.content:
                                            b64 = base64.b64encode(resp.content).decode()
                                            ct = resp.headers.get("content-type", "image/png")
                                            icon_html = f"<img src='data:{ct};base64,{b64}'>"
                                            self._gift_icon_cache[gift_name.lower()] = icon_url
                                            self._gift_b64_cache[gift_name.lower()] = icon_html
                                else:
                                    # DEBUG: O que temos no objeto gift?
                                    print(f"⚠️ [DEBUG] Gift sem URL encontrada. dir(gift): {dir(gift_obj)}")
                                    if hasattr(gift_obj, 'image'):
                                        print(f"   gift.image = {gift_obj.image}")
                                    if hasattr(gift_obj, 'icon'):
                                        print(f"   gift.icon = {gift_obj.icon}")
                            except Exception as e:
                                print(f"⚠️ [DEBUG] Erro no fallback do gift: {e}")

                        msg = get_translation("gift_sent_multiple", self.language, gift_name, icon_html, gift_count)
                        self.message_received.emit(author, msg, "tiktok")
                    except Exception as e:
                        print(f"⚠️ Erro ao processar presente: {e}")


                @self.client.on(FollowEvent)
                async def on_follow(event: FollowEvent):
                    try:
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        msg = get_translation("follow_started", self.language)
                        self.message_received.emit(author, msg, "tiktok")
                    except:
                        pass

                @self.client.on(ShareEvent)
                async def on_share(event: ShareEvent):
                    try:
                        author = getattr(event.user, 'nickname', getattr(event.user, 'nick_name', "Usuário"))
                        msg = get_translation("share_transmitted", self.language)
                        self.message_received.emit(author, msg, "tiktok")
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
                    self.status_changed.emit(True)
                    if not self._already_connected:
                        msg = get_translation("tiktok_connected", self.language, username=self.username)
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                        self._already_connected = True
                    
                    # Marca o timestamp de conexão para backup do uptime
                    self._start_ts = int(time.time())
                    
                    # Popula o cache de ícones e tenta a primeira busca de uptime
                    await _build_gift_cache()
                    
                    # Tenta buscar o uptime logo ao conectar, fornecendo o room_id explicitamente
                    if not self._create_time:
                        try:
                            rid = getattr(self.client, 'room_id', None)
                            r_dict = await self.client.web.fetch_room_info(room_id=rid)
                            if isinstance(r_dict, dict):
                                ct = r_dict.get('create_time') or r_dict.get('createTime') or r_dict.get('start_time')
                                if not ct:
                                    room = r_dict.get('room', r_dict.get('data', {}).get('room', {}))
                                    if isinstance(room, dict):
                                        ct = room.get('create_time') or room.get('createTime')
                                if ct:
                                    self._create_time = int(ct)
                                    if self._create_time > 2000000000:
                                        self._create_time //= 1000
                            self._room_info_fetched = True
                        except:
                            pass

                @self.client.on(DisconnectEvent)
                async def on_disconnect(event: DisconnectEvent):
                    if self.is_running:
                        self.status_changed.emit(False)
                        self._already_connected = False

                self.message_received.emit(
                    get_translation("tiktok_connect_attempt", self.language),
                    get_translation("tiktok_attempting", self.language, username=self.username),
                    "system"
                )
                self.status_changed.emit(True)
                loop_task = await self.client.start()
                await loop_task

                if self.is_running:
                    self.status_changed.emit(False)
                    self.message_received.emit(
                        get_translation("tiktok_connect_attempt", self.language),
                        get_translation("tiktok_disconnected", self.language),
                        "system"
                    )

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate_limit" in error_str or "too many connections" in error_str:
                    self._rate_limited = True
                    if self.is_running:
                        self.status_changed.emit(False)
                        msg = get_translation("tiktok_rate_limited", self.language, username=self.username, error=str(e)[:100])
                        self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
                    self.is_running = False
                elif self.is_running:
                    self.status_changed.emit(False)
                    msg = get_translation("tiktok_error", self.language, error=str(e))
                    self.message_received.emit(get_translation("tiktok_connect_attempt", self.language), msg, "system")
            finally:
                self.client = None

        asyncio.run_coroutine_threadsafe(run_tiktok(), self.loop)

    def stop(self):
        self.is_running = False
        if self.client and self.loop:
            try:
                asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            except Exception as e:
                print(f"⚠️ Erro ao parar TikTok: {e}")

    def is_rate_limited(self):
        return self._rate_limited

    def reset_rate_limit(self):
        self._rate_limited = False
