import socket
import threading
import time
import httpx
from .base_handler import BaseChatHandler
from utils.emoticons import convert_emoticons, get_emote_url, resolve_7tv_emote
from utils.translations import get_translation

class TwitchHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "twitch"
        self.sock = None
        self.is_running = False

    def start(self):
        if not self.username:
            return
        
        self.is_running = True
        
        # Carrega badges de assinante/bits específicas do canal em background
        try:
            from utils.badge_manager import badge_manager
            badge_manager.load_twitch_channel_badges(self.username)
        except Exception:
            pass

        self.thread = threading.Thread(target=self._run_irc, daemon=True)
        self.thread.start()
        # Thread paralela de polling de viewers (a cada 60s via GQL)
        self._viewers_thread = threading.Thread(target=self._poll_viewers, daemon=True)
        self._viewers_thread.start()

    def _poll_viewers(self):
        """Faz polling do viewer count da Twitch via GQL público a cada 60 segundos."""
        channel = self.username.lower().replace('#', '')
        query = """
        query StreamInfo($login: String!) {
          user(login: $login) {
            stream { viewersCount }
          }
        }
        """
        headers = {
            "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json",
        }
        # Aguarda 5s para a conexão IRC estabelecer antes do primeiro poll
        time.sleep(5)
        while self.is_running:
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        "https://gql.twitch.tv/gql",
                        json=[{"query": query, "variables": {"login": channel}}],
                        headers=headers
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        stream = data[0].get("data", {}).get("user", {}).get("stream") or {}
                        viewers = stream.get("viewersCount", 0) if stream else 0
                        # Emite viewers reais mantendo uptime/likes como 0 (não afeta outros campos)
                        self.stats_updated.emit(viewers, 0, 0, 0)
            except Exception as e:
                print(f"[Twitch] Erro ao buscar viewers: {e}")
            # Polling a cada 30 segundos (bom equilíbrio sem risco de rate limit)
            for _ in range(30):
                if not self.is_running:
                    break
                time.sleep(1)

    def _run_irc(self):
        while self.is_running:
            try:
                channel = self.username.lower().replace('#', '')
                self.sock = socket.socket()
                self.sock.settimeout(10)
                self.sock.connect(('irc.chat.twitch.tv', 6667))
                
                # Login anônimo (justinfan)
                self.sock.send(f"PASS SCHMOOPIIE\r\n".encode('utf-8'))
                self.sock.send(f"NICK justinfan{int(time.time()) % 10000}\r\n".encode('utf-8'))
                self.sock.send(f"CAP REQ :twitch.tv/tags\r\n".encode('utf-8'))
                self.sock.send(f"JOIN #{channel}\r\n".encode('utf-8'))
                
                print(f"✅ Comandos de login enviados para Twitch.")
                msg = get_translation("twitch_connected", self.language, channel)
                self.message_received.emit(get_translation("twitch_connect_attempt", self.language), msg, "system")
                self.status_changed.emit(True)
                self.stats_updated.emit(0, 0, 0, 0) # Dispara Failsafe pro Cronômetro Genérico
                
                # Buffer para acumular dados e processar apenas linhas completas (\r\n)
                # Resolve o problema de fragmentação de metadados no chat
                buffer = ""
                
                # Manter conexão estável
                while self.is_running:
                    try:
                        data = self.sock.recv(4096).decode('utf-8', errors='ignore')
                        if not data:
                            break
                        
                        buffer += data
                        while '\r\n' in buffer:
                            line, buffer = buffer.split('\r\n', 1)
                            if not line: continue
                            
                            if line.startswith('PING'):
                                self.sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
                                continue

                            if 'PRIVMSG' in line:
                                tags = {}
                                main_part = line
                                if line.startswith('@'):
                                    try:
                                        tags_part, main_part = line[1:].split(' ', 1)
                                        # Parse de tags IRC nativas
                                        tags = {item.split('=')[0]: item.split('=')[1] for item in tags_part.split(';') if '=' in item}
                                    except: pass

                                try:
                                    # Formato padrão: :user!user@user.tmi.twitch.tv PRIVMSG #channel :message
                                    if '!' in main_part and 'PRIVMSG' in main_part:
                                        user = main_part.split('!')[0].replace(':', '').strip()
                                        message_parts = main_part.split('PRIVMSG', 1)[1].split(':', 1)
                                        if len(message_parts) > 1:
                                            message = message_parts[1]
                                            
                                            # Processar emoticons da Twitch via tags
                                            emotes_tag = tags.get('emotes', '')
                                            if emotes_tag:
                                                replacements = []
                                                for emote_data in emotes_tag.split('/'):
                                                    if ':' not in emote_data: continue
                                                    eid, positions = emote_data.split(':')
                                                    for pos in positions.split(','):
                                                        if '-' not in pos: continue
                                                        start, end = map(int, pos.split('-'))
                                                        replacements.append((start, end, eid))
                                                
                                                # Inverter a ordem das substituições para manter os índices originais válidos
                                                replacements.sort(key=lambda x: x[0], reverse=True)
                                                for s, e, eid in replacements:
                                                    img_url = f"https://static-cdn.jtvnw.net/emoticons/v2/{eid}/default/dark/1.0"
                                                    # Obter a URL local do arquivo (file:///)
                                                    emote_src = get_emote_url(img_url, eid)
                                                    
                                                    if emote_src:
                                                        img_tag = f"<img src='{emote_src}' width='20' height='20' style='vertical-align: middle;'>"
                                                        message = message[:s] + img_tag + message[e+1:]
                                                    else:
                                                        # Se falhar o download, mantemos o texto original
                                                        pass

                                            # 1. Processar emoticons baseados em texto (aliases locais)
                                            message = convert_emoticons(message)
                                            
                                            # 2. Processar emotes de terceiros (7TV/BTTV) por nome
                                            # Isso resolve casos como 'thimag1Risada' mencionadas pelo usuário
                                            words = message.split(' ')
                                            new_words = []
                                            for word in words:
                                                # Limpar o nome do emote de pontuações básicas
                                                clean_word = word.strip('.,!?()[]{}')
                                                tv_url, tv_id = resolve_7tv_emote(clean_word)
                                                if tv_url:
                                                    tv_src = get_emote_url(tv_url, tv_id)
                                                    if tv_src:
                                                        img_tag = f"<img src='{tv_src}' width='20' height='20' style='vertical-align: middle;'>"
                                                        new_words.append(word.replace(clean_word, img_tag))
                                                    else:
                                                        new_words.append(word)
                                                else:
                                                    new_words.append(word)
                                            
                                            message = ' '.join(new_words)

                                            # Processar badges oficiais da Twitch (Moderador, VIP, Subscritor, etc.)
                                            display_name = tags.get('display-name') or user
                                            badges_tag = tags.get('badges', '')
                                            badge_str = ''
                                            if badges_tag:
                                                try:
                                                    from utils.badge_manager import badge_manager
                                                    badge_str = badge_manager.get_twitch_badges_html(badges_tag)
                                                except Exception:
                                                    pass

                                            author_display = f"{badge_str} {display_name}".strip() if badge_str else display_name
                                            self.message_received.emit(author_display, message, "twitch")
                                except Exception as e:
                                    print(f"💥 Erro ao processar linha IRC: {e}")
                                    pass
                    except socket.timeout:
                        continue
            except Exception as e:
                if self.is_running:
                    self.status_changed.emit(False)
                    msg = get_translation("twitch_disconnected", self.language, str(e))
                    self.message_received.emit(get_translation("twitch_connect_attempt", self.language), msg, "system")
            finally:
                if self.sock:
                    try: self.sock.close()
                    except: pass
            
            # Aguardar antes de reconectar, apenas se ainda está rodando
            if self.is_running:
                for _ in range(30):
                    if not self.is_running: break
                    time.sleep(1)
                self.sock = None
                
            if self.is_running:
                for _ in range(30):
                    if not self.is_running: break
                    time.sleep(1)
                
        # Fora do loop while self.is_running
        self.stop()

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None
