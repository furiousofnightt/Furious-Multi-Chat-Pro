from kickpython import KickAPI
from .base_handler import BaseChatHandler
from utils.emoticons import convert_emoticons
from utils.translations import get_translation
from utils.resource_path import resource_path
import threading
import asyncio

class KickHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "kick"
        self.api = None
        self.loop = None
        self.task = None

    def start_with_loop(self, loop):
        self.loop = loop
        self.is_running = True
        self.api = KickAPI()
        self.connected = False
        
        async def on_kick_message(data):
            try:
                author = data.get('sender_username', 'Desconhecido')
                content = data.get('content', '')
                badges = data.get('badges', [])
                # Mapeamento de badge para SVG
                badge_svgs = {
                    'MOD': 'mod.svg',
                    'MODERADOR': 'moderador.svg',
                    'MODERATOR': 'moderador.svg',
                    'VIP': 'vip.svg',
                    'STREAMER': 'kick_broadcaster.svg',
                    'BROADCASTER': 'kick_broadcaster.svg',
                    'OG': 'og.svg',
                    'FUNDADOR': 'fundador.svg',
                    'FOUNDER': 'fundador.svg',
                    'SUBSCRIBER': 'subscriber.svg',
                    'SUB GIFTER': 'kick_sub_gifter.svg',
                    'VERIFIED CHANNEL': 'kick_verified.svg',
                    'VERIFIED': 'kick_verified.svg',
                }
                badge_str = ''
                for b in badges:
                    svg_file = badge_svgs.get(b.upper()) or badge_svgs.get(b.capitalize())
                    if svg_file:
                        svg_path = resource_path(f"assets/{svg_file}")
                        badge_str += f" <img src='file:///{svg_path.replace('\\','/')}' width='18' height='18' style='vertical-align: middle; margin-left:6px; margin-right:2px;'>"
                    elif b:
                        badge_str += f" <span style='margin-left:6px;'>[{b}]</span>"
                if badge_str:
                    author = f"{author}{badge_str}"
                
                import re
                from utils.emoticons import get_emote_url, convert_emoticons
                
                # 1. Processar emoticons do Kick via Regex (Resolve os códigos [emote:ID:NAME])
                # Usamos re.finditer para encontrar todos os placeholders mesmo que a API não liste
                emote_pattern = r'\[emote:(\d+):([^\]]+)\]'
                matches = list(re.finditer(emote_pattern, content))
                
                # Processar do fim para o começo para manter os índices válidos
                for match in reversed(matches):
                    eid = match.group(1)
                    ename = match.group(2)
                    start, end = match.span()
                    
                    # URL padrão da Kick para emotes
                    eurl = f"https://files.kick.com/emotes/{eid}/fullsize"
                    
                    # Obter a URL local (estabilidade total)
                    local_url = get_emote_url(eurl, f"kick_{eid}")
                    
                    if local_url:
                        img_tag = f"<img src='{local_url}' width='20' height='20' style='vertical-align: middle;'>"
                        content = content[:start] + img_tag + content[end:]
                
                # 2. Converter emoticons de texto legados (aliases)
                content = convert_emoticons(content)
                
                # Primeira mensagem confirma conexão
                if not self.connected:
                    self.connected = True
                    msg = get_translation("kick_connected", self.language, self.username)
                    self.message_received.emit(get_translation("kick_connect_attempt", self.language), msg, "system")
                    self.status_changed.emit(True)
                    self.stats_updated.emit(0, 0, 0, 0) # Dispara Failsafe pro Cronômetro Genérico
                
                self.message_received.emit(author, content, "kick")
            except:
                pass

        async def connect_and_listen():
            if self.is_running:
                msg = get_translation("kick_connecting", self.language, self.username)
                self.message_received.emit(get_translation("kick_connect_attempt", self.language), msg, "system")
            
            # Conexão mantém-se aberta naturalmente sem reconexões forçadas
            await self.api.connect_to_chatroom(self.username)

        self.api.add_message_handler(on_kick_message)
        
        # Disparar a conexão no loop compartilhado
        self.task = asyncio.run_coroutine_threadsafe(
            connect_and_listen(), 
            self.loop
        )
        
        # Iniciar polling de viewers do Kick
        async def poll_viewers():
            import sqlite3
            import os
            try:
                from curl_cffi import requests
            except ImportError:
                print("[Kick] curl_cffi não encontrado, não será possível atualizar viewers.")
                return
                
            await asyncio.sleep(5)
            while self.is_running:
                try:
                    token = None
                    if os.path.exists("kick_tokens.db"):
                        try:
                            conn = sqlite3.connect("kick_tokens.db")
                            row = conn.execute("SELECT access_token FROM tokens LIMIT 1").fetchone()
                            if row:
                                token = row[0]
                            conn.close()
                        except Exception: pass
                            
                    headers = {
                        "Accept": "application/json",
                    }
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                        
                    resp = requests.get(
                        f"https://kick.com/api/v2/channels/{self.username}", 
                        headers=headers,
                        impersonate="chrome120",
                        timeout=10
                    )
                    
                    if resp.status_code == 200:
                        if not self.connected:
                            self.connected = True
                            msg = get_translation("kick_connected", self.language, self.username)
                            self.message_received.emit(get_translation("kick_connect_attempt", self.language), msg, "system")
                            self.status_changed.emit(True)
                            
                        data = resp.json()
                        ls = data.get("livestream") or data.get("live_stream")
                        viewers = ls.get("viewer_count", 0) if ls else 0
                        self.stats_updated.emit(viewers, 0, 0, 0)
                except Exception as e:
                    print(f"[Kick] Erro ao buscar viewers: {e}")
                    
                for _ in range(30):
                    if not self.is_running: break
                    await asyncio.sleep(1)
                    
        self.viewers_task = asyncio.run_coroutine_threadsafe(poll_viewers(), self.loop)

    def stop(self):
        self.is_running = False
        if self.task:
            try: self.task.cancel()
            except: pass
        if hasattr(self, 'viewers_task') and self.viewers_task:
            try: self.viewers_task.cancel()
            except: pass
            
        if self.api and self.loop:
            try:
                # KickAPI.close é assíncrono
                asyncio.run_coroutine_threadsafe(self.api.close(), self.loop)
            except Exception as e:
                print(f"⚠️ Erro ao parar Kick: {e}")
