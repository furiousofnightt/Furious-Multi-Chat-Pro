from PyQt6.QtCore import QObject, pyqtSignal

class BaseChatHandler(QObject):
    message_received = pyqtSignal(str, str, str)  # (user, text, platform)
    user_joined = pyqtSignal(str, str)           # (username, platform)
    status_changed = pyqtSignal(bool)            # (connected)
    stats_updated = pyqtSignal(int, int, int)     # (viewers, uptime_seconds, likes)
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.is_running = False
        self.language = "pt-br"  # Idioma padrão

    def start(self):
        raise NotImplementedError

    def stop(self):
        self.is_running = False
    
    def set_language(self, lang):
        """Define o idioma para as mensagens de sistema"""
        self.language = lang
