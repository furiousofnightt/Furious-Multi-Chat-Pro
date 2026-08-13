"""
HotkeyManager — Sistema de Atalhos de Teclado Global
Roda em thread separada para capturar teclas mesmo quando o app não tem foco (durante gameplay).
"""
import keyboard
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    """Gerencia hotkeys globais configuráveis pelo usuário."""
    
    # Sinais enviados para a thread da UI (thread-safe)
    toggle_visibility_requested = pyqtSignal()
    clear_chat_requested = pyqtSignal()
    toggle_tts_requested = pyqtSignal()
    toggle_clickthrough_requested = pyqtSignal()
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings = settings_manager
        self._registered = []
        self._lock = threading.Lock()
    
    def start(self):
        """Registra todos os hotkeys configurados nas settings."""
        self._unregister_all()
        s = self.settings.settings
        
        hotkey_toggle = s.get("hotkey_toggle_visibility", "ctrl+shift+h")
        hotkey_clear  = s.get("hotkey_clear_chat",       "ctrl+shift+c")
        hotkey_tts    = s.get("hotkey_toggle_tts",       "ctrl+m")
        hotkey_clickthrough = s.get("hotkey_clickthrough", "ctrl+alt+t")
        
        self._register(hotkey_toggle, self.toggle_visibility_requested.emit)
        self._register(hotkey_clear,  self.clear_chat_requested.emit)
        self._register(hotkey_tts,    self.toggle_tts_requested.emit)
        self._register(hotkey_clickthrough, self.toggle_clickthrough_requested.emit)
    
    def _register(self, combo: str, callback):
        """Registra um atalho com tratamento de erro (combo inválida não quebra o app)."""
        if not combo or combo.strip() == "":
            return
        try:
            keyboard.add_hotkey(combo.strip(), callback, suppress=False)
            self._registered.append(combo.strip())
        except Exception as e:
            print(f"⚠️ Hotkey inválida '{combo}': {e}")
    
    def _unregister_all(self):
        """Remove todos os hotkeys anteriores antes de re-registrar."""
        with self._lock:
            for combo in self._registered:
                try:
                    keyboard.remove_hotkey(combo)
                except Exception:
                    pass
            self._registered.clear()
    
    def stop(self):
        """Para todos os hotkeys (chamado ao fechar o app)."""
        self._unregister_all()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
