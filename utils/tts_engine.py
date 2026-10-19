import os
import re
import sys
import time
import tempfile
import asyncio
import threading
import logging
from datetime import datetime
from collections import deque
from PyQt6.QtCore import QObject, QTimer

logger = logging.getLogger("TTSManager")

# Arquivo de log persistente para diagnóstico da sessão atual
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tts_debug.log")
MAX_LOG_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB máximo por sessão durante transmissões longas (3-5h)
_session_initialized = False

# Garante UTF-8 no stdout do Windows se possível
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def init_session_log():
    """
    Inicia uma sessão de logs limpa a cada abertura do aplicativo/transmissão.
    Se já houver log da sessão anterior, faz backup seguro para .old e recria o arquivo zerado.
    """
    global _session_initialized
    try:
        if os.path.exists(LOG_FILE_PATH):
            old_path = LOG_FILE_PATH + ".old"
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
                os.rename(LOG_FILE_PATH, old_path)
            except Exception:
                pass
                
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("=" * 65 + "\n")
            f.write("[SISTEMA] FURIOUS MULTI CHAT PRO - NOVA SESSAO TTS INICIADA\n")
            f.write(f"Data/Hora de Inicio: {now_str}\n")
            f.write("Os logs desta sessao sao mantidos de forma limpa e rotativa.\n")
            f.write("=" * 65 + "\n\n")
        _session_initialized = True
    except Exception:
        pass

def _rotate_session_log():
    """Mantém apenas as últimas 500 linhas se o arquivo ultrapassar 2MB durante lives longas."""
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] [LIMPEZA] Mantidas as ultimas 500 linhas para economizar espaco.\n")
            f.writelines(lines[-500:])
    except Exception:
        pass

def log_tts(level_name: str, message: str):
    """
    Registra logs formatados do TTS no terminal (stdout), no logger padrão e em arquivo.
    100% livre de emoticons/emojis para total compatibilidade em compilações Windows (PyInstaller).
    """
    global _session_initialized
    if not _session_initialized:
        init_session_log()

    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] [TTS] {message}"
    
    # Exibir no console imediatamente (com tratamento para Windows cp1252)
    try:
        print(formatted_msg, flush=True)
    except UnicodeEncodeError:
        try:
            encoding = getattr(sys.stdout, "encoding", "ascii") or "ascii"
            safe_text = formatted_msg.encode(encoding, errors="replace").decode(encoding)
            print(safe_text, flush=True)
        except Exception:
            pass
    except Exception:
        pass
        
    # Salvar no arquivo de log da sessão atual
    try:
        # Prevenção contra arquivos gigantes em lives de 3-5h: rotaciona se ultrapassar 2MB
        if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > MAX_LOG_SIZE_BYTES:
            _rotate_session_log()

        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level_name}] {message}\n")
    except Exception:
        pass

    # Enviar para o logger oficial
    if level_name == "ERROR":
        logger.error(message)
    elif level_name == "WARNING":
        logger.warning(message)
    elif level_name == "DEBUG":
        logger.debug(message)
    else:
        logger.info(message)


try:
    import pygame
    import edge_tts
    from utils.edge_tts_compat import apply_edge_tts_compat
    apply_edge_tts_compat()
    TTS_AVAILABLE = True
except ImportError as e:
    log_tts("WARNING", f"[AVISO] Biblioteca edge-tts ou pygame nao disponivel: {e}")
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
        super().__init__(parent if isinstance(parent, QObject) else None)
        init_session_log()
        self.parent_window = parent
        self.settings = getattr(parent, "settings_manager", None)
        # Fila protegida contra raid (no máximo 10 na fila)
        self.queue = deque(maxlen=10) # Armazena os caminhos dos arquivos .mp3
        self.downloading_count = 0
        self.is_muted = False
        self.current_playing_file = None
        self.current_channel = None
        self.play_start_time = None
        self.download_semaphore = None
        
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
                log_tts("INFO", "[MIXER] Mixer de audio (pygame) inicializado com sucesso.")
            except Exception as e:
                log_tts("ERROR", f"[ERRO] Falha ao iniciar mixer de audio para TTS: {e}")
                
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Timer para checar a fila
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_queue)
        self.timer.start(300)

        log_tts("INFO", f"[STATUS] TTSManager pronto. Motores: [Edge TTS: {'OK' if TTS_AVAILABLE else 'Ausente'}] [Google TTS: {'OK' if GTTS_AVAILABLE else 'Ausente'}]")

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        # Cria semáforo para evitar que múltiplos downloads paralelos inundem o servidor da Microsoft
        self.download_semaphore = asyncio.Semaphore(1)
        self.loop.run_forever()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            log_tts("INFO", "[MUTE] Bot de voz SILENCIADO pelo usuario. Fila esvaziada.")
            self.clear_queue()
        else:
            log_tts("INFO", "[SOM] Bot de voz REATIVADO pelo usuario.")
        return self.is_muted

    def clear_queue(self):
        cleared_count = len(self.queue)
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
                if pygame.mixer.get_init():
                    try: pygame.mixer.music.unload()
                    except: pass
                if os.path.exists(self.current_playing_file):
                    os.remove(self.current_playing_file)
            except:
                pass
            self.current_playing_file = None
        self.current_channel = None
        self.play_start_time = None
        if cleared_count > 0:
            log_tts("DEBUG", f"[LIMPEZA] Fila limpa: {cleared_count} audio(s) descartado(s).")

    def add_message(self, user, text, platform="twitch"):
        settings = getattr(self.parent_window, "settings_manager", None)
        blacklist = settings.settings.get("blacklist", []) if settings else []
        clean_text = TextCleaner.clean(text, blacklist=blacklist)
        clean_user = TextCleaner.clean(user, blacklist=blacklist)

        # Loga nome e texto limpos (sem base64 ou tags HTML de badges)
        log_tts("DEBUG", f"[MSG] Recebida de '{clean_user}' [{platform.upper()}]: '{clean_text}'")

        if not TTS_AVAILABLE:
            log_tts("WARNING", "[AVISO] Ignorada: Biblioteca TTS nao disponivel.")
            return

        if self.is_muted:
            log_tts("DEBUG", f"[MUTE] Ignorada de '{clean_user}': Bot de voz silenciado.")
            return
            
        if settings:
            if not settings.settings.get("tts_enabled", True):
                log_tts("DEBUG", f"[PAUSA] Ignorada de '{clean_user}': Leitura global de chat desativada.")
                return
            if not settings.settings.get(f"tts_enabled_{platform}", True):
                log_tts("DEBUG", f"[PAUSA] Ignorada de '{clean_user}': TTS desativado para a plataforma '{platform}'.")
                return
            
        if not clean_text:
            log_tts("DEBUG", f"[PULO] Ignorada de '{clean_user}': Texto vazio apos limpeza/blacklist.")
            return
            
        # Impede spam de downloads simultâneos e acúmulo infinito
        total_pending = len(self.queue) + self.downloading_count
        if total_pending >= 10:
            log_tts("WARNING", f"[FILA CHEIA] Descartada: '{clean_user}: {clean_text[:30]}...' (Itens na fila: {len(self.queue)}, Baixando: {self.downloading_count}, Limite: 10)")
            return
            
        message_to_read = f"{clean_user} disse: {clean_text}"
        
        voice = self.default_voices.get(platform, "pt-BR-FranciscaNeural")
        if settings:
            voice = settings.settings.get(f"tts_voice_{platform}", voice)
        
        self.downloading_count += 1
        log_tts("INFO", f"[ACEITA] '{message_to_read}' [Plataforma: {platform} | Voz: {voice}]")
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
        is_channel_busy = bool(self.current_channel and self.current_channel.get_busy())
        is_music_busy = bool(pygame.mixer.music.get_busy())

        # Watchdog: Se um áudio ficar ocupado por mais de 35 segundos, força a liberação
        if is_channel_busy or is_music_busy:
            if self.play_start_time and (time.time() - self.play_start_time > 35):
                log_tts("WARNING", "[WATCHDOG] Audio travado ha mais de 35s. Forcando liberacao do mixer.")
                try:
                    if self.current_channel: self.current_channel.stop()
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                self.current_channel = None
                self.play_start_time = None
            else:
                return
            
        # Limpa arquivo temporário anterior após o término
        if getattr(self, "current_playing_file", None):
            try:
                if pygame.mixer.get_init():
                    try: pygame.mixer.music.unload()
                    except: pass
                if os.path.exists(self.current_playing_file):
                    os.remove(self.current_playing_file)
                log_tts("DEBUG", "[STOP] Reproducao finalizada. Arquivo temporario removido.")
            except Exception as e:
                log_tts("DEBUG", f"[NOTA] Remocao de arquivo temporario: {e}")
            self.current_playing_file = None
            self.current_channel = None
            self.play_start_time = None
            
        if self.queue:
            temp_path = self.queue.popleft()
            try:
                vol = (settings.settings.get("tts_volume", 100) / 100.0) if settings else 1.0
                file_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                
                try:
                    # Método 1: Sound em memória (sem trava de stream de arquivo)
                    sound = pygame.mixer.Sound(temp_path)
                    sound.set_volume(vol)
                    self.current_channel = sound.play()
                    self.current_playing_file = temp_path
                    self.play_start_time = time.time()
                    log_tts("INFO", f"[PLAY] Audio ({file_size} bytes, Volume: {int(vol*100)}%) | Restam na fila: {len(self.queue)}")
                except Exception as ex_sound:
                    # Método 2: Fallback para music
                    log_tts("DEBUG", f"Fallback para pygame.mixer.music: {ex_sound}")
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.set_volume(vol)
                    pygame.mixer.music.play()
                    self.current_playing_file = temp_path
                    self.play_start_time = time.time()
                    log_tts("INFO", f"[PLAY via music] Audio ({file_size} bytes, Volume: {int(vol*100)}%) | Restam na fila: {len(self.queue)}")
            except Exception as e:
                log_tts("ERROR", f"[ERRO] Falha ao reproduzir TTS: {e}")
                if os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except: pass

    async def _download_and_queue(self, text, voice):
        """Roteador de motor TTS com fila de download serializada e fallback automático."""
        settings = getattr(self.parent_window, "settings_manager", None)
        engine = settings.settings.get("tts_engine", "edge") if settings else "edge"

        try:
            # Semáforo garante que solicitações não ocorram em rajadas paralelas simultâneas
            if self.download_semaphore is None:
                self.download_semaphore = asyncio.Semaphore(1)

            async with self.download_semaphore:
                if engine == "google":
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._download_gtts, text
                    )
                else:
                    # Motor Edge TTS com fallback automático para Google se a Microsoft falhar
                    success = await self._download_edge(text, voice)
                    if not success and GTTS_AVAILABLE:
                        log_tts("WARNING", f"[CONTINGENCIA] Edge TTS falhou para '{text[:30]}...'. Acionando fallback para Google TTS...")
                        await asyncio.get_event_loop().run_in_executor(
                            None, self._download_gtts, text
                        )
        except Exception as e:
            log_tts("ERROR", f"[ERRO] Erro critico em _download_and_queue: {e}")
        finally:
            self.downloading_count = max(0, self.downloading_count - 1)

    async def _download_edge(self, text, voice) -> bool:
        """Motor: Microsoft Edge TTS com timeout e diagnóstico detalhado."""
        temp_path = None
        t0 = time.time()
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()

            log_tts("INFO", f"[EDGE] Sintetizando via Microsoft Edge (Voz: {voice})...")
            communicate = edge_tts.Communicate(text, voice)
            
            # Timeout de 12 segundos para não prender a fila se a conexão cair
            await asyncio.wait_for(communicate.save(temp_path), timeout=12.0)

            size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
            elapsed = time.time() - t0

            if size == 0:
                log_tts("ERROR", "[EDGE] Arquivo de audio gerado vazio (0 bytes).")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

            # Se mutou durante o download, descarta
            settings = getattr(self.parent_window, "settings_manager", None)
            if self.is_muted or (settings and not settings.settings.get("tts_enabled", True)):
                log_tts("DEBUG", "[EDGE] Descartando audio gerado pois o bot foi silenciado durante o download.")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

            self.queue.append(temp_path)
            log_tts("INFO", f"[OK] [EDGE] Audio gerado com sucesso ({size} bytes em {elapsed:.2f}s) -> Enfileirado (Fila: {len(self.queue)})")
            return True

        except asyncio.TimeoutError:
            log_tts("ERROR", "[EDGE] Timeout de 12s excedido ao conectar no servidor Microsoft.")
            if temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            return False
        except Exception as e:
            elapsed = time.time() - t0
            log_tts("ERROR", f"[EDGE] Erro no motor Edge TTS apos {elapsed:.2f}s: {e}")
            if temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            return False

    def _download_gtts(self, text) -> bool:
        """Motor alternativo: Google TTS (gTTS). Roda em thread executor."""
        temp_path = None
        t0 = time.time()
        try:
            if not GTTS_AVAILABLE:
                log_tts("WARNING", "[GOOGLE] gTTS nao instalado. Instale com: pip install gtts")
                return False

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()

            log_tts("INFO", "[GOOGLE] Sintetizando via Google TTS...")
            tts = GoogleTTS(text=text, lang="pt", slow=False)
            tts.save(temp_path)

            size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
            elapsed = time.time() - t0

            if size == 0:
                log_tts("ERROR", "[GOOGLE] Arquivo gerado vazio (0 bytes).")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

            # Se mutou durante o download, descarta
            settings = getattr(self.parent_window, "settings_manager", None)
            if self.is_muted or (settings and not settings.settings.get("tts_enabled", True)):
                log_tts("DEBUG", "[GOOGLE] Descartando audio gerado pois o bot foi silenciado.")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

            self.queue.append(temp_path)
            log_tts("INFO", f"[OK] [GOOGLE] Audio gerado com sucesso ({size} bytes em {elapsed:.2f}s) -> Enfileirado (Fila: {len(self.queue)})")
            return True

        except Exception as e:
            elapsed = time.time() - t0
            log_tts("ERROR", f"[GOOGLE] Erro no motor Google TTS apos {elapsed:.2f}s: {e}")
            if temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            return False
