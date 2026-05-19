from PyQt6.QtCore import QObject, pyqtSignal, QTimer
# Importações dos handlers
from chat_handlers.twitch_handler import TwitchHandler
from chat_handlers.tiktok_handler import TikTokHandler
from chat_handlers.kick_handler import KickHandler
from utils.translations import get_translation
import asyncio
import threading

class AsyncManager(threading.Thread):
    def __init__(self, manager):
        super().__init__(daemon=True)
        self.manager = manager
        self.loop = None
        self.loop_ready = threading.Event()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop_ready.set()
        self.loop.run_forever()

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

class ChatManager(QObject):
    status_changed = pyqtSignal(str, bool)

    def __init__(self, settings, window):
        super().__init__()
        self.settings = settings
        self.window = window
        self.handlers = []
        self.message_queue = []
        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self.process_message_queue)
        
        self.async_manager = AsyncManager(self)
        self.async_manager.start()
        
        # Estado de conexão
        self.statuses = {"twitch": False, "tiktok": False, "kick": False}
        
        # Conectar sinal de comandos da UI
        self.window.command_executed.connect(self.handle_command)

    def handle_command(self, cmd):
        lang = self.settings.settings.get("language", "pt-br")
        if cmd.lower() == "/clear":
            self.window.clear_chat()
            self.window.add_message("Sistema", get_translation("chat_cleared", lang), "system")
        elif cmd.lower() == "/config":
            self.window.settings_requested.emit()
        else:
            self.window.add_message("Sistema", get_translation("unknown_command", lang, cmd=cmd), "system")

    def start_all(self):
        self.window.clear_chat()
        self.window.reset_live_stats()
        self.message_queue.clear()
        self.message_timer.stop()
        lang = self.settings.settings.get("language", "pt-br")
        
        # Garantir que o loop async está pronto
        if not self.async_manager.loop_ready.wait(timeout=10):
            print("❌ Erro: Loop assíncrono não iniciou em 10 segundos.")
            return
        
        # Twitch
        if self.settings.settings.get("twitch"):
            h = TwitchHandler(self.settings.settings["twitch"])
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("twitch", connected))
            h.stats_updated.connect(self.window.update_live_stats)
            self.update_status("twitch", False) # Status inicial: vermelho (tentando)
            h.start()
            self.handlers.append(h)


        # TikTok e Kick usam o AsyncManager
        if self.settings.settings.get("tiktok"):
            h = TikTokHandler(self.settings.settings["tiktok"])
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("tiktok", connected))
            h.stats_updated.connect(self.window.update_live_stats)
            self.update_status("tiktok", False) # Status inicial: vermelho (tentando)
            # Executado na thread principal, o handler se encarrega de jogar pro loop
            h.start_with_loop(self.async_manager.loop)
            self.handlers.append(h)

        if self.settings.settings.get("kick"):
            h = KickHandler(self.settings.settings["kick"])
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("kick", connected))
            h.stats_updated.connect(self.window.update_live_stats)
            self.update_status("kick", False)
            h.start_with_loop(self.async_manager.loop)
            self.handlers.append(h)

    def update_status(self, platform, connected):
        self.statuses[platform] = connected
        self.status_changed.emit(platform, connected)

    def filter_message(self, message):
        """ Filtra palavras da blacklist substituindo por asteriscos """
        blacklist = self.settings.settings.get("blacklist", [])
        if not blacklist:
            return message
            
        filtered_message = message
        import re
        for word in blacklist:
            # Filtro case-insensitive que preserva pontuação ao redor
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            filtered_message = pattern.sub("*****", filtered_message)
            
        return filtered_message

    def on_message_received(self, author, message, platform):
        # Aplicar filtro de palavras
        filtered_msg = self.filter_message(message)
        
        delay_seconds = float(self.settings.settings.get("message_delay", 0))
        if delay_seconds > 0:
            self.message_queue.append((author, filtered_msg, platform))
            if not self.message_timer.isActive():
                self.message_timer.start(int(delay_seconds * 1000))
        else:
            self.window.add_message(author, filtered_msg, platform)
            
    def process_message_queue(self):
        if self.message_queue:
            author, msg, platform = self.message_queue.pop(0)
            self.window.add_message(author, msg, platform)
            
            # Ajustar o tempo caso a configuração tenha mudado no meio
            delay_seconds = float(self.settings.settings.get("message_delay", 0))
            if delay_seconds == 0:
                # Se desligar a lentidão, despeja tudo
                for o_author, o_msg, o_plat in self.message_queue:
                    self.window.add_message(o_author, o_msg, o_plat)
                self.message_queue.clear()
                self.message_timer.stop()
            elif self.message_timer.interval() != int(delay_seconds * 1000):
                self.message_timer.setInterval(int(delay_seconds * 1000))
        else:
            self.message_timer.stop()

    def restart_all(self):
        # Parar apenas os handlers, manter o loop vivo
        self.stop_all(total_stop=False)
        QTimer.singleShot(1000, self.start_all)

    def stop_all(self, total_stop=True):
        # Parar todos os handlers (Twitch/TikTok/Kick)
        for h in self.handlers:
            try:
                h.stop()
            except Exception as e:
                print(f"⚠️ Erro ao parar handler {getattr(h, 'platform', 'unknown')}: {e}")
            
        self.handlers = []
        
        # Parar o loop assíncrono apenas se for encerramento total
        if total_stop and self.async_manager:
            try:
                self.async_manager.stop()
            except Exception as e:
                print(f"⚠️ Erro ao parar AsyncManager: {e}")
            
        for p in self.statuses:
            self.statuses[p] = False
            self.status_changed.emit(p, False)
        
        print("🛑 Todos os processos de chat foram encerrados.")
