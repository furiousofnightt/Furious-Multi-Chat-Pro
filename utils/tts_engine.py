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
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


class TextCleaner:
    @staticmethod
    def clean(text):
        """Limpa o texto removendo HTML e links para o bot ler corretamente."""
        # Remove tags HTML
        clean_text = re.sub(r'<[^>]+>', '', text)
        # Substitui links por 'link enviado'
        clean_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 'link enviado', clean_text)
        # Remove emojis e caracteres estranhos
        clean_text = re.sub(r'[^\w\s.,!?@#&*-]', '', clean_text)
        # Reduz letras repetidas (ex: kkkkkkk -> kkk)
        clean_text = re.sub(r'(.)\1{4,}', r'\1\1\1', clean_text)
        return clean_text.strip()


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
        
        self.default_voices = {
            "twitch": "pt-BR-AntonioNeural",
            "tiktok": "pt-BR-FranciscaNeural",
            "kick": "pt-BR-ThalitaMultilingualNeural",
            "system": "pt-BR-FranciscaNeural"
        }
        
        if TTS_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"⚠️ Erro ao iniciar mixer de áudio para TTS: {e}")
                
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Timer para ler a fila
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_queue)
        self.timer.start(500)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.clear_queue()
        return self.is_muted

    def clear_queue(self):
        # Exclui todos os arquivos pendentes
        for temp_path in self.queue:
            try:
                os.remove(temp_path)
            except:
                pass
                
        self.queue.clear()
        if TTS_AVAILABLE and pygame.mixer.get_init():
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        
        if getattr(self, "current_playing_file", None):
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.unload()
                os.remove(self.current_playing_file)
            except:
                pass
            self.current_playing_file = None

    def add_message(self, user, text, platform="twitch"):
        if not TTS_AVAILABLE or self.is_muted:
            return
            
        settings = getattr(self.parent_window, "settings_manager", None)
        if settings:
            if not settings.settings.get("tts_enabled", True):
                return
            if not settings.settings.get(f"tts_enabled_{platform}", True):
                return
            
        clean_text = TextCleaner.clean(text)
        clean_user = TextCleaner.clean(user)
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
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.clear_queue()
            return
            
        # Checa se o mixer está rodando
        if not pygame.mixer.get_init():
            return

        if pygame.mixer.music.get_busy():
            return
            
        # Deleta o arquivo que acabou de tocar
        if getattr(self, "current_playing_file", None):
            try:
                pygame.mixer.music.unload()
                os.remove(self.current_playing_file)
            except:
                pass
            self.current_playing_file = None
            
        if self.queue:
            temp_path = self.queue.popleft()
            try:
                if settings:
                    vol = settings.settings.get("tts_volume", 100) / 100.0
                    pygame.mixer.music.set_volume(vol)
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                self.current_playing_file = temp_path
            except Exception as e:
                print(f"⚠️ Erro ao reproduzir TTS: {e}")

    async def _download_and_queue(self, text, voice):
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
                os.remove(temp_path)
                return
                
            self.queue.append(temp_path)
                
        except Exception as e:
            print(f"⚠️ Erro no motor TTS: {e}")
            if temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
        finally:
            self.downloading_count = max(0, self.downloading_count - 1)
