import os
import re
import tempfile
import asyncio
import threading
from collections import deque
from PyQt6.QtCore import QObject, QTimer

try:
    import pygame
    import edge_tts
    from utils.edge_tts_compat import apply_edge_tts_compat
    apply_edge_tts_compat()
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    from gtts import gTTS as GoogleTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class TextCleaner:
    @staticmethod
    def clean(text, blacklist=None):
        """Limpa o texto removendo HTML, emojis e caracteres inválidos para o bot ler corretamente."""
        if not text:
            return ""
        # Normalizar apóstrofos e acentos soltos usados como apóstrofos
        text = text.replace('´', "'").replace('`', "'").replace('’', "'")
        # Substitui & por 'e' para evitar quebra de XML/SSML no Edge-TTS
        text = text.replace('&', ' e ')
        # Remove tags HTML (ex: <img>, <span>)
        clean_text = re.sub(r'<[^>]+>', '', text)
        # Substitui links por 'link enviado'
        clean_text = re.sub(r'https?://\S+|www\.\S+', 'link enviado', clean_text)
        
        # Filtra palavras da blacklist para o bot de voz não falar termos proibidos
        if blacklist:
            for word in blacklist:
                if word:
                    boundary = r'(?<![A-Za-zÀ-ÿ0-9_])' + re.escape(word) + r'(?![A-Za-zÀ-ÿ0-9_])'
                    clean_text = re.sub(boundary, '', clean_text, flags=re.IGNORECASE)

        # Remove emojis e caracteres fora do alfabeto/pontuação comum
        clean_text = re.sub(r"[^\w\s.,!?@#'*-]", '', clean_text)
        # Reduz letras repetidas excessivas (ex: kkkkkkkk -> kkk)
        clean_text = re.sub(r'(.)\1{4,}', r'\1\1\1', clean_text)
        clean_text = clean_text.strip()
        # Limite máximo de segurança de 500 caracteres (suporta o tamanho máximo da Twitch/Kick)
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."
        return clean_text


class TTSManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = getattr(parent, "settings_manager", None)
        # Fila protegida contra raid (no máximo 10 na fila)
        self.queue = deque(maxlen=10) # Armazena os caminhos dos arquivos .mp3
        self.downloading_count = 0
        self.is_muted = False
        self.current_playing_file = None
        self.current_channel = None
        
        self.default_voices = {
            "twitch": "pt-BR-AntonioNeural",
            "tiktok": "pt-BR-FranciscaNeural",
            "kick": "pt-BR-ThalitaMultilingualNeural",
            "youtube": "pt-BR-AntonioNeural",
            "system": "pt-BR-FranciscaNeural"
        }
        
        if TTS_AVAILABLE:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            except Exception as e:
                print(f"⚠️ Erro ao iniciar mixer de áudio para TTS: {e}")
                
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Timer para checar a fila
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_queue)
        self.timer.start(300)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.clear_queue()
        return self.is_muted

    def clear_queue(self):
        if self.current_channel and self.current_channel.get_busy():
            try: self.current_channel.stop()
            except: pass
        if TTS_AVAILABLE and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            try: pygame.mixer.music.stop()
            except: pass
            
        for temp_path in list(self.queue):
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
        self.queue.clear()
        
        if getattr(self, "current_playing_file", None):
            try:
                if os.path.exists(self.current_playing_file):
                    os.remove(self.current_playing_file)
            except:
                pass
            self.current_playing_file = None
        self.current_channel = None

    def add_message(self, user, text, platform="twitch"):
        if not TTS_AVAILABLE or self.is_muted:
            return
            
        settings = getattr(self.parent_window, "settings_manager", None)
        if settings:
            if not settings.settings.get("tts_enabled", True):
                return
            if not settings.settings.get(f"tts_enabled_{platform}", True):
                return
            
        blacklist = settings.settings.get("blacklist", []) if settings else []
        clean_text = TextCleaner.clean(text, blacklist=blacklist)
        clean_user = TextCleaner.clean(user, blacklist=blacklist)
        if not clean_text:
            return
            
        # Impede spam de downloads simultâneos e acúmulo infinito
        if len(self.queue) + self.downloading_count >= 10:
            return
            
        message_to_read = f"{clean_user} disse: {clean_text}"
        
        voice = self.default_voices.get(platform, "pt-BR-FranciscaNeural")
        if settings:
            voice = settings.settings.get(f"tts_voice_{platform}", voice)
        
        self.downloading_count += 1
        asyncio.run_coroutine_threadsafe(self._download_and_queue(message_to_read, voice), self.loop)

    def _check_queue(self):
        if not TTS_AVAILABLE or self.is_muted:
            return
            
        settings = getattr(self.parent_window, "settings_manager", None)
        if settings and not settings.settings.get("tts_enabled", True):
            self.clear_queue()
            return
            
        if not pygame.mixer.get_init():
            return

        # Verifica se o áudio atual ainda está tocando
        is_channel_busy = (self.current_channel and self.current_channel.get_busy())
        is_music_busy = pygame.mixer.music.get_busy()
        if is_channel_busy or is_music_busy:
            return
            
        # Limpa arquivo temporário anterior após o término
        if getattr(self, "current_playing_file", None):
            try:
                if os.path.exists(self.current_playing_file):
                    os.remove(self.current_playing_file)
            except:
                pass
            self.current_playing_file = None
            self.current_channel = None
            
        if self.queue:
            temp_path = self.queue.popleft()
            try:
                vol = (settings.settings.get("tts_volume", 100) / 100.0) if settings else 1.0
                try:
                    # Método 1: Sound em memória (sem trava de stream de arquivo)
                    sound = pygame.mixer.Sound(temp_path)
                    sound.set_volume(vol)
                    self.current_channel = sound.play()
                    self.current_playing_file = temp_path
                except Exception:
                    # Método 2: Fallback para music
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.set_volume(vol)
                    pygame.mixer.music.play()
                    self.current_playing_file = temp_path
            except Exception as e:
                print(f"⚠️ Erro ao reproduzir TTS: {e}")

    async def _download_and_queue(self, text, voice):
        """Roteador de motor TTS: usa Google ou Edge conforme configuração."""
        settings = getattr(self.parent_window, "settings_manager", None)
        engine = settings.settings.get("tts_engine", "edge") if settings else "edge"

        if engine == "google":
            # Roda gTTS em thread separada pois é síncrono
            await asyncio.get_event_loop().run_in_executor(
                None, self._download_gtts, text
            )
        else:
            # Motor original Edge TTS — código intocado
            await self._download_edge(text, voice)

    async def _download_edge(self, text, voice):
        """Motor original: Microsoft Edge TTS (edge-tts). Código intocado."""
        temp_path = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_path)

            # Se mutou durante o download, descarta
            settings = getattr(self.parent_window, "settings_manager", None)
            if self.is_muted or (settings and not settings.settings.get("tts_enabled", True)):
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return

            self.queue.append(temp_path)

        except Exception as e:
            print(f"⚠️ Erro no motor TTS (Edge): {e}")
            if temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
        finally:
            self.downloading_count = max(0, self.downloading_count - 1)

    def _download_gtts(self, text):
        """Motor alternativo: Google TTS (gTTS). Roda em thread executor."""
        temp_path = None
        try:
            if not GTTS_AVAILABLE:
                print("⚠️ gTTS não está instalado. Instale com: pip install gtts")
                return

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()

            tts = GoogleTTS(text=text, lang="pt", slow=False)
            tts.save(temp_path)

            # Se mutou durante o download, descarta
            settings = getattr(self.parent_window, "settings_manager", None)
            if self.is_muted or (settings and not settings.settings.get("tts_enabled", True)):
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return

            self.queue.append(temp_path)

        except Exception as e:
            print(f"⚠️ Erro no motor TTS (Google): {e}")
            if temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
        finally:
            self.downloading_count = max(0, self.downloading_count - 1)
