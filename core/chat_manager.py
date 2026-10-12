from PyQt6.QtCore import QObject, pyqtSignal, QTimer
# Importações dos handlers
from chat_handlers.twitch_handler import TwitchHandler
from chat_handlers.tiktok_handler import TikTokHandler
from chat_handlers.kick_handler import KickHandler
from chat_handlers.youtube_handler import YoutubeHandler
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
    platform_stats_updated = pyqtSignal(str, int, int, int, int) # platform, viewers, uptime, likes, total_views

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
        self.statuses = {"twitch": False, "tiktok": False, "kick": False, "youtube": False}
        # Viewers por plataforma (para tooltip)
        self._platform_viewers = {"twitch": 0, "tiktok": 0, "kick": 0, "youtube": 0}
        
        # Conectar sinal de comandos da UI
        self.window.command_executed.connect(self.handle_command)
        
        # Conectar sinal de stats para garantir execução na thread da GUI
        self.platform_stats_updated.connect(self._on_platform_stats)

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
        
        # Reset internal states
        self._platform_viewers = {"twitch": 0, "tiktok": 0, "kick": 0, "youtube": 0}
        self.statuses = {"twitch": False, "tiktok": False, "kick": False, "youtube": False}
        self.window.update_secondary_viewers(self._platform_viewers.copy(), self.statuses.copy())
        
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
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("twitch", v, u, l, t))
            self.update_status("twitch", False)
            h.start()
            self.handlers.append(h)

        # YouTube
        if self.settings.settings.get("youtube"):
            h = YoutubeHandler(self.settings.settings["youtube"])
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("youtube", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("youtube", v, u, l, t))
            self.update_status("youtube", False)
            h.start()  # usa threading nativo
            self.handlers.append(h)


        # TikTok e Kick usam o AsyncManager
        if self.settings.settings.get("tiktok"):
            h = TikTokHandler(self.settings.settings["tiktok"])
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("tiktok", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("tiktok", v, u, l, t))
            if hasattr(self.window, "update_tiktok_viewers"):
                h.viewers_list_updated.connect(self.window.update_tiktok_viewers)
            self.update_status("tiktok", False)
            h.start_with_loop(self.async_manager.loop)
            self.handlers.append(h)

        if self.settings.settings.get("kick"):
            h = KickHandler(self.settings.settings["kick"])
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("kick", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("kick", v, u, l, t))
            self.update_status("kick", False)
            h.start_with_loop(self.async_manager.loop)
            self.handlers.append(h)

    def update_status(self, platform, connected):
        self.statuses[platform] = connected
        if not connected:
            self._platform_viewers[platform] = 0
            
        self.status_changed.emit(platform, connected)
        self.window.update_secondary_viewers(self._platform_viewers.copy(), self.statuses.copy())
        if not connected:
            # Limpa fila de "fulano entrou na live" da plataforma que desconectou
            if hasattr(self.window, 'clear_platform_joins'):
                self.window.clear_platform_joins(platform)
            self._refresh_main_stats()

    def _refresh_main_stats(self):
        """Atualiza a HUD principal quando um chat desconecta, garantindo que o fallback funcione ou limpe tudo se for o último."""
        # Se nenhuma plataforma estiver conectada, apenas reseta os contadores da HUD (não apaga as mensagens da tela)
        if not any(self.statuses.values()):
            self.window.reset_live_stats()
            return
            
        # Se TikTok estiver online, não faz nada (ele gerencia sozinho)
        if self.statuses.get("tiktok", False):
            return
            
        # Tenta achar o próximo substituto online para dominar a HUD
        for p in ("twitch", "kick", "youtube"):
            if self.statuses.get(p, False):
                v = self._platform_viewers.get(p, 0)
                self.window.update_live_stats(v, 0, 0, 0)
                return

    def _resolve_viewer_value(self, platform, viewers):
        """Evita que valores temporários 0 do TikTok derrubem o tooltip e o contador."""
        try:
            viewers = int(viewers)
        except Exception:
            viewers = 0

        if platform == "tiktok" and viewers == 0 and self.statuses.get(platform, False):
            previous = self._platform_viewers.get(platform, 0)
            if previous > 0:
                return previous

        return viewers

    def _on_platform_stats(self, platform, viewers, uptime_seconds, likes, total_views=0):
        """
        Centraliza os stats de todas as plataformas.
        - TikTok é o primário: uptime + likes só vem do TikTok.
        - Viewers de Twitch/Kick são armazenados e exibidos no tooltip.
        """
        effective_viewers = self._resolve_viewer_value(platform, viewers)

        # Armazena e notifica a UI, preservando o último valor válido do TikTok quando ele manda 0 temporariamente.
        self._platform_viewers[platform] = effective_viewers
        self.window.update_secondary_viewers(self._platform_viewers.copy(), self.statuses.copy())

        # Somente TikTok alimenta o painel principal de stats (uptime + likes)
        if platform == "tiktok":
            self.window.update_live_stats(effective_viewers, uptime_seconds, likes, total_views)
        elif platform in ("twitch", "kick", "youtube"):
            # Twitch/Kick/YouTube: só passa viewers para o display principal
            # se o TikTok não estiver conectado (fallback)
            if not self.statuses.get("tiktok", False):
                self.window.update_live_stats(effective_viewers, uptime_seconds, likes, total_views)

    def filter_message(self, message):
        """
        Filtra palavras da blacklist substituindo por asteriscos.
        Usa word boundaries que respeitam acentuação para evitar censurar
        substrings dentro de palavras normais (ex: 'anal' na blacklist não
        deve censurar a palavra 'canal').
        """
        blacklist = self.settings.settings.get("blacklist", [])
        if not blacklist:
            return message
            
        filtered_message = message
        import re
        for word in blacklist:
            # Lookarounds negativos: o caractere antes e depois não pode ser
            # alfanumérico nem acentuado. Isso garante apenas palavras isoladas.
            boundary = r'(?<![A-Za-zÀ-ÿ0-9_])' + re.escape(word) + r'(?![A-Za-zÀ-ÿ0-9_])'
            pattern = re.compile(boundary, re.IGNORECASE)
            filtered_message = pattern.sub("*" * len(word), filtered_message)
            
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

    def restart_platform(self, platform):
        # Parar handler existente dessa plataforma
        for h in list(self.handlers):
            if getattr(h, "platform", "") == platform:
                try:
                    h.stop()
                except Exception as e:
                    print(f"⚠️ Erro ao parar handler {platform}: {e}")
                for sig_name in ("message_received", "user_joined", "status_changed", "stats_updated", "viewers_list_updated"):
                    sig = getattr(h, sig_name, None)
                    if sig:
                        try:
                            sig.disconnect()
                        except Exception:
                            pass
                self.handlers.remove(h)
        
        self._platform_viewers[platform] = 0
        self.update_status(platform, False)
        
        lang = self.settings.settings.get("language", "pt-br")
        username = self.settings.settings.get(platform)
        if not username:
            # Username removido desta plataforma
            if hasattr(self.window, 'clear_platform_joins'):
                self.window.clear_platform_joins(platform)

            if platform == "tiktok":
                if hasattr(self.window, 'clear_tiktok_viewers'):
                    self.window.clear_tiktok_viewers()
                elif hasattr(self.window, 'viewers_page') and self.window.viewers_page:
                    self.window.viewers_page.clear_viewers()

            # Só limpa o chat completo se TODAS as plataformas estiverem sem canal configurado
            all_empty = not any(self.settings.settings.get(p) for p in ("twitch", "tiktok", "kick", "youtube"))
            if all_empty and hasattr(self.window, 'clear_chat'):
                self.window.clear_chat()
            return
            
        if platform == "twitch":
            h = TwitchHandler(username)
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("twitch", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("twitch", v, u, l, t))
            h.start()
            self.handlers.append(h)
        elif platform == "youtube":
            h = YoutubeHandler(username)
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("youtube", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("youtube", v, u, l, t))
            h.start()
            self.handlers.append(h)
        elif platform == "tiktok":
            h = TikTokHandler(username)
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("tiktok", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("tiktok", v, u, l, t))
            if hasattr(self.window, "update_tiktok_viewers"):
                h.viewers_list_updated.connect(self.window.update_tiktok_viewers)
            h.start_with_loop(self.async_manager.loop)
            self.handlers.append(h)
        elif platform == "kick":
            h = KickHandler(username)
            h.set_language(lang)
            h.message_received.connect(self.on_message_received)
            h.user_joined.connect(self.window.add_user_joined)
            h.status_changed.connect(lambda connected: self.update_status("kick", connected))
            h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("kick", v, u, l, t))
            h.start_with_loop(self.async_manager.loop)
            self.handlers.append(h)


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

        if hasattr(self.window, 'clear_tiktok_viewers'):
            self.window.clear_tiktok_viewers()
        elif hasattr(self.window, 'viewers_page') and self.window.viewers_page:
            self.window.viewers_page.clear_viewers()
        
        print("🛑 Todos os processos de chat foram encerrados.")
