import json
import uuid
import re
import asyncio
import threading
import websockets
from curl_cffi import requests as creq
from .base_handler import BaseChatHandler
from utils.emoticons import convert_emoticons, get_emote_url
from utils.translations import get_translation
from utils.resource_path import resource_path

class KickHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "kick"
        self.loop = None
        self.task = None
        self.viewers_task = None
        self.chatroom_id = None
        self.ws = None

    def start_with_loop(self, loop):
        self.loop = loop
        self.is_running = True
        self.connected = False

        # Carrega catálogo de badges do canal se houver
        try:
            from utils.badge_manager import badge_manager
            if hasattr(badge_manager, 'load_kick_channel_badges'):
                badge_manager.load_kick_channel_badges(self.username)
        except Exception:
            pass

        async def get_channel_info():
            """Obtém chatroom_id e dados do canal via API oficial v2."""
            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            try:
                # Executa a requisição síncrona do curl_cffi em threadpool para não travar o loop
                resp = await self.loop.run_in_executor(
                    None,
                    lambda: creq.get(
                        f"https://kick.com/api/v2/channels/{self.username}",
                        headers=headers,
                        impersonate="chrome124",
                        timeout=12
                    )
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cid = data.get("chatroom", {}).get("id")
                    if cid:
                        self.chatroom_id = str(cid)
                    # Registra badges de assinante no badge_manager imediatamente
                    sub_badges = data.get("subscriber_badges", []) or []
                    if sub_badges:
                        try:
                            from utils.badge_manager import badge_manager
                            ch_map = {}
                            for sb in sub_badges:
                                m = sb.get("months", 1)
                                s_url = sb.get("badge_image", {}).get("src", "")
                                if s_url:
                                    ch_map[m] = s_url
                            with badge_manager._kick_lock:
                                badge_manager._kick_sub_badges[self.username.lower()] = ch_map
                                badge_manager._kick_channel_loaded = self.username.lower()
                        except Exception:
                            pass
                    return data
            except Exception as e:
                print(f"[Kick] Erro ao buscar dados do canal {self.username}: {e}")
            return None

        async def get_connection_token(client_id):
            """Obtém o token público (guest JWT) para autenticação no Centrifugo."""
            req_body = {"client_id": client_id}
            req_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://kick.com",
                "Referer": "https://kick.com/",
                "x-app-platform": "web"
            }
            try:
                resp = await self.loop.run_in_executor(
                    None,
                    lambda: creq.post(
                        "https://web.kick.com/api/v1/realtime/auth/connection",
                        json=req_body,
                        headers=req_headers,
                        impersonate="chrome124",
                        timeout=10
                    )
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("token")
            except Exception as e:
                print(f"[Kick] Erro ao obter token do Centrifugo: {e}")
            return None

        def format_kick_message(inner_data):
            """Processa badges, emotes e emite a mensagem para o chat."""
            try:
                sender = inner_data.get("sender", {})
                author = sender.get("username", "Desconhecido")
                content = inner_data.get("content", "")
                
                # Monta badges oficiais da Kick via badge_manager
                badge_str = ""
                try:
                    from utils.badge_manager import badge_manager
                    identity = sender.get("identity", {})
                    b_list = identity.get("badges", [])
                    b_v2 = identity.get("badges_v2", [])
                    badge_str = badge_manager.get_kick_badges_html(b_list, self.username, badges_v2=b_v2)
                except Exception as e:
                    print(f"[Kick] Erro ao renderizar badges: {e}")

                if badge_str:
                    author = f"{badge_str} {author}".strip()

                # Processa emoticons do Kick via Regex: [emote:ID:NAME]
                emote_pattern = r'\[emote:(\d+):([^\]]+)\]'
                matches = list(re.finditer(emote_pattern, content))
                for match in reversed(matches):
                    eid = match.group(1)
                    start, end = match.span()
                    eurl = f"https://files.kick.com/emotes/{eid}/fullsize"
                    local_url = get_emote_url(eurl, f"kick_{eid}")
                    if local_url:
                        img_tag = f"<img src='{local_url}' width='20' height='20' style='vertical-align: middle;'>"
                        content = content[:start] + img_tag + content[end:]

                # Converte emoticons de texto legados
                content = convert_emoticons(content)

                # Confirma conexão caso ainda não tenha sido
                if not self.connected:
                    self.connected = True
                    msg = get_translation("kick_connected", self.language, self.username)
                    self.message_received.emit(get_translation("kick_connect_attempt", self.language), msg, "system")
                    self.status_changed.emit(True)
                    self.stats_updated.emit(0, 0, 0, 0)

                self.message_received.emit(author, content, "kick")
            except Exception as e:
                print(f"[Kick] Erro ao formatar mensagem: {e}")

        async def connect_and_listen():
            if self.is_running:
                msg = get_translation("kick_connecting", self.language, self.username)
                self.message_received.emit(get_translation("kick_connect_attempt", self.language), msg, "system")

            while self.is_running:
                try:
                    # 1. Obtém chatroom_id
                    if not self.chatroom_id:
                        ch_data = await get_channel_info()
                        if not self.chatroom_id:
                            print(f"[Kick] Não foi possível encontrar chatroom_id para {self.username}. Tentando em 5s...")
                            await asyncio.sleep(5)
                            continue

                    # 2. Gera novo client_id e obtém token do Centrifugo
                    client_id = str(uuid.uuid4())
                    token = await get_connection_token(client_id)
                    if not token:
                        print("[Kick] Falha ao obter token de acesso. Tentando em 5s...")
                        await asyncio.sleep(5)
                        continue

                    # 3. Conecta no WebSocket oficial do Centrifugo do Kick
                    ws_url = "wss://realtime.us-west-2.platform.kick.com/connection/websocket"
                    headers_ws = [
                        ("Origin", "https://kick.com"),
                        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
                    ]

                    async with websockets.connect(
                        ws_url,
                        additional_headers=headers_ws,
                        open_timeout=15,
                        ping_interval=None # Centrifugo faz keep-alive próprio com pong
                    ) as ws:
                        self.ws = ws

                        # Envia comando connect com o token obtido
                        await ws.send(json.dumps({"id": 1, "connect": {"token": token}}))
                        resp_connect = await asyncio.wait_for(ws.recv(), timeout=10)
                        
                        # Inscreve no canal do chat
                        channel_name = f"chatrooms.{self.chatroom_id}.v2"
                        await ws.send(json.dumps({"id": 2, "subscribe": {"channel": channel_name}}))
                        resp_sub = await asyncio.wait_for(ws.recv(), timeout=10)

                        if not self.connected:
                            self.connected = True
                            msg = get_translation("kick_connected", self.language, self.username)
                            self.message_received.emit(get_translation("kick_connect_attempt", self.language), msg, "system")
                            self.status_changed.emit(True)

                        print(f"[Kick] Conectado e inscrito com sucesso no chatroom {self.chatroom_id} ({self.username})!")

                        # Inicia renovação proativa do token sem derrubar a conexão (keep-alive)
                        ttl = 2700
                        try:
                            parsed_conn = json.loads(resp_connect)
                            ttl = parsed_conn.get("connect", {}).get("ttl", 2700)
                        except Exception:
                            pass

                        async def refresh_loop():
                            refresh_interval = max(60, ttl - 300) # renova 5 min antes de expirar
                            while self.is_running and self.ws == ws:
                                await asyncio.sleep(refresh_interval)
                                if not self.is_running or self.ws != ws:
                                    break
                                try:
                                    new_token = await get_connection_token(client_id)
                                    if new_token:
                                        await ws.send(json.dumps({"id": 999, "refresh": {"token": new_token}}))
                                        print("[Kick] Sessão Centrifugo renovada com sucesso (sem desconectar)!")
                                except Exception as e:
                                    print(f"[Kick] Falha ao renovar token proativo: {e}")

                        refresher_task = asyncio.create_task(refresh_loop())

                        try:
                            # Loop de recebimento de mensagens
                            while self.is_running:
                                raw_msg = await ws.recv()
                                # Centrifugo pode enviar mensagens NDJSON (separadas por \n)
                                for line in raw_msg.strip().split("\n"):
                                    line = line.strip()
                                    if not line:
                                        continue
                                    # Ping do Centrifugo: responde com {}
                                    if line == "{}":
                                        await ws.send("{}")
                                        continue

                                    try:
                                        payload = json.loads(line)
                                    except Exception:
                                        continue

                                    # Verifica se é uma publicação (push)
                                    push = payload.get("push")
                                    if push and "pub" in push:
                                        pub_data = push["pub"].get("data", {})
                                        event_type = pub_data.get("event")
                                        if event_type == "App\\Events\\ChatMessageEvent":
                                            raw_inner = pub_data.get("data")
                                            if isinstance(raw_inner, str):
                                                try:
                                                    inner = json.loads(raw_inner)
                                                except Exception:
                                                    inner = {}
                                            else:
                                                inner = raw_inner or {}

                                            if inner:
                                                format_kick_message(inner)
                        finally:
                            refresher_task.cancel()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[Kick] Conexão WebSocket reiniciando: {e}")
                    self.connected = False
                    self.status_changed.emit(False)
                    await asyncio.sleep(4)

        self.task = asyncio.run_coroutine_threadsafe(connect_and_listen(), self.loop)

        # Polling de viewers da live
        async def poll_viewers():
            await asyncio.sleep(3)
            while self.is_running:
                try:
                    headers = {
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    }
                    resp = await self.loop.run_in_executor(
                        None,
                        lambda: creq.get(
                            f"https://kick.com/api/v2/channels/{self.username}",
                            headers=headers,
                            impersonate="chrome124",
                            timeout=10
                        )
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        ls = data.get("livestream") or data.get("live_stream")
                        viewers = ls.get("viewer_count", 0) if ls else 0
                        self.stats_updated.emit(viewers, 0, 0, 0)
                except Exception as e:
                    print(f"[Kick] Erro ao buscar viewers: {e}")

                for _ in range(30):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)

        self.viewers_task = asyncio.run_coroutine_threadsafe(poll_viewers(), self.loop)

    def stop(self):
        self.is_running = False
        self.connected = False
        if self.ws:
            try:
                asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
            except Exception:
                pass
        if self.task:
            try:
                self.task.cancel()
            except Exception:
                pass
        if self.viewers_task:
            try:
                self.viewers_task.cancel()
            except Exception:
                pass
