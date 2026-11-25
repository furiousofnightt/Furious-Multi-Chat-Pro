"""
HotkeyManager — Sistema de Atalhos de Teclado Global Dinâmico (Win32 RegisterHotKey)
Usa a API nativa oficial do Windows via ctypes e resolução dinâmica de teclas com QKeySequence e VkKeyScanW.
Sem ganchos de teclado (hooks) globais, totalmente seguro, sem falso positivo de antivírus e com latência zero (0% CPU).
"""
import ctypes
import threading
from ctypes import wintypes
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = wintypes.BOOL

user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

user32.VkKeyScanW.argtypes = [ctypes.c_wchar]
user32.VkKeyScanW.restype = ctypes.c_short

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Mapeamento oficial e abrangente de teclas especiais do Qt para Virtual Keys (VK) do Windows
QT_KEY_TO_VK = {
    Qt.Key.Key_Escape: 0x1B,
    Qt.Key.Key_Tab: 0x09,
    Qt.Key.Key_Backtab: 0x09,
    Qt.Key.Key_Backspace: 0x08,
    Qt.Key.Key_Return: 0x0D,
    Qt.Key.Key_Enter: 0x0D,
    Qt.Key.Key_Insert: 0x2D,
    Qt.Key.Key_Delete: 0x2E,
    Qt.Key.Key_Pause: 0x13,
    Qt.Key.Key_Print: 0x2C,
    Qt.Key.Key_Home: 0x24,
    Qt.Key.Key_End: 0x23,
    Qt.Key.Key_Left: 0x25,
    Qt.Key.Key_Up: 0x26,
    Qt.Key.Key_Right: 0x27,
    Qt.Key.Key_Down: 0x28,
    Qt.Key.Key_PageUp: 0x21,
    Qt.Key.Key_PageDown: 0x22,
    Qt.Key.Key_CapsLock: 0x14,
    Qt.Key.Key_NumLock: 0x90,
    Qt.Key.Key_ScrollLock: 0x91,
    Qt.Key.Key_Space: 0x20,
    Qt.Key.Key_VolumeDown: 0xAE,
    Qt.Key.Key_VolumeUp: 0xAF,
    Qt.Key.Key_VolumeMute: 0xAD,
    Qt.Key.Key_MediaPlay: 0xB3,
    Qt.Key.Key_MediaStop: 0xB2,
    Qt.Key.Key_MediaPrevious: 0xB1,
    Qt.Key.Key_MediaNext: 0xB0,
}

# Teclas de Função F1 a F24 dinâmicas
for _i in range(1, 25):
    _k = getattr(Qt.Key, f'Key_F{_i}', None)
    if _k:
        QT_KEY_TO_VK[_k] = 0x70 + (_i - 1)


def parse_hotkey(combo: str) -> tuple[int, int]:
    """
    Resolve dinamicamente qualquer combinação de teclas para (modifiers, vk) do Windows.
    Combina o parser universal QKeySequence do Qt com a API VkKeyScanW do Windows para
    suportar qualquer layout de teclado (ABNT2, US, etc.) e qualquer atalho digitado pelo usuário.
    """
    if not combo or not str(combo).strip():
        return 0, 0

    clean_str = str(combo).strip()

    # 1. Tenta resolução dinâmica via QKeySequence
    ks = QKeySequence(clean_str)
    if not ks.isEmpty():
        k_comb = ks[0]
        raw_mod = k_comb.toCombined() & int(Qt.KeyboardModifier.KeyboardModifierMask.value)
        raw_key = k_comb.toCombined() & ~int(Qt.KeyboardModifier.KeyboardModifierMask.value)

        win_mod = MOD_NOREPEAT
        if raw_mod & int(Qt.KeyboardModifier.ControlModifier.value):
            win_mod |= MOD_CONTROL
        if raw_mod & int(Qt.KeyboardModifier.AltModifier.value):
            win_mod |= MOD_ALT
        if raw_mod & int(Qt.KeyboardModifier.ShiftModifier.value):
            win_mod |= MOD_SHIFT
        if raw_mod & int(Qt.KeyboardModifier.MetaModifier.value):
            win_mod |= MOD_WIN

        qt_enum = Qt.Key(raw_key)
        if qt_enum in QT_KEY_TO_VK:
            return win_mod, QT_KEY_TO_VK[qt_enum]

        # Caracteres padrão (letras e números)
        if 0x20 <= raw_key <= 0x7E:
            char = chr(raw_key).upper()
            if 'A' <= char <= 'Z' or '0' <= char <= '9':
                return win_mod, ord(char)
            # Caracteres pontuação/símbolos consultados diretamente no layout ativo do Windows
            scan = user32.VkKeyScanW(char)
            if scan != -1:
                return win_mod, scan & 0xFF
            return win_mod, ord(char)

    # 2. Resolução dinâmica de texto puro (fallback para strings informais como 'del', 'pgdown')
    parts = [p.strip().lower() for p in clean_str.replace('+', ' ').split() if p.strip()]
    win_mod = MOD_NOREPEAT
    vk = 0
    mod_map = {
        'ctrl': MOD_CONTROL, 'control': MOD_CONTROL,
        'shift': MOD_SHIFT,
        'alt': MOD_ALT,
        'win': MOD_WIN, 'windows': MOD_WIN
    }

    aliases = {
        'pgup': 0x21, 'pageup': 0x21, 'prior': 0x21,
        'pgdown': 0x22, 'pagedown': 0x22, 'pgdn': 0x22, 'next': 0x22,
        'del': 0x2E, 'delete': 0x2E,
        'ins': 0x2D, 'insert': 0x2D,
        'esc': 0x1B, 'escape': 0x1B,
        'space': 0x20, 'tab': 0x09, 'enter': 0x0D, 'return': 0x0D,
        'backspace': 0x08, 'home': 0x24, 'end': 0x23,
        'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
        'printscreen': 0x2C, 'prtscr': 0x2C, 'prtsc': 0x2C, 'print': 0x2C,
        'pause': 0x13, 'capslock': 0x14, 'scrolllock': 0x91, 'numlock': 0x90,
        'apps': 0x5D, 'menu': 0x5D,
    }
    # Numpad (0-9 e operações)
    for _i in range(10):
        aliases[f'numpad{_i}'] = 0x60 + _i
        aliases[f'num{_i}'] = 0x60 + _i
        aliases[f'numpad_{_i}'] = 0x60 + _i
        aliases[f'kp{_i}'] = 0x60 + _i
        aliases[f'kp_{_i}'] = 0x60 + _i
    aliases['numpadmultiply'] = 0x6A
    aliases['numpadmul'] = 0x6A
    aliases['numpadadd'] = 0x6B
    aliases['numpadseparator'] = 0x6C
    aliases['numpadsubtract'] = 0x6D
    aliases['numpadsub'] = 0x6D
    aliases['numpaddecimal'] = 0x6E
    aliases['numpaddivide'] = 0x6F
    aliases['numpaddiv'] = 0x6F

    for p in parts:
        clean = p.replace('_', '').replace('-', '')
        if p in mod_map or clean in mod_map:
            win_mod |= mod_map.get(p, mod_map.get(clean, 0))
        elif p in aliases or clean in aliases:
            vk = aliases.get(p, aliases.get(clean, 0))
        elif p.startswith('f') and p[1:].isdigit() and 1 <= int(p[1:]) <= 24:
            vk = 0x70 + (int(p[1:]) - 1)
        elif len(p) == 1:
            scan = user32.VkKeyScanW(p)
            if scan != -1:
                vk = scan & 0xFF
            else:
                vk = ord(p.upper())

    return win_mod, vk


class HotkeyManager(QObject):
    """Gerencia hotkeys globais nativas do Windows dinamicamente sem hooks de teclado."""

    # Sinais enviados para a thread da UI (thread-safe)
    toggle_visibility_requested = pyqtSignal()
    clear_chat_requested = pyqtSignal()
    toggle_tts_requested = pyqtSignal()
    toggle_clickthrough_requested = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()
        self.settings = settings_manager
        self._thread = None
        self._thread_id = None
        self._running = False
        self._callbacks = {}
        self._lock = threading.Lock()

    def start(self):
        """Inicia a thread de escuta nativa dos atalhos configurados dinamicamente."""
        self.stop()
        with self._lock:
            s = self.settings.settings
            hotkeys = [
                (1, s.get("hotkey_toggle_visibility", "ctrl+shift+h"), self.toggle_visibility_requested.emit),
                (2, s.get("hotkey_clear_chat", "ctrl+shift+c"), self.clear_chat_requested.emit),
                (3, s.get("hotkey_toggle_tts", "ctrl+m"), self.toggle_tts_requested.emit),
                (4, s.get("hotkey_clickthrough", "ctrl+alt+t"), self.toggle_clickthrough_requested.emit),
            ]
            self._callbacks = {hk_id: cb for hk_id, combo, cb in hotkeys}
            self._running = True
            ready_event = threading.Event()
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(hotkeys, ready_event),
                daemon=True,
                name="Win32HotkeyThread"
            )
            self._thread.start()
            ready_event.wait(timeout=1.0)

    def _run_loop(self, hotkeys, ready_event):
        """Loop de mensagens Win32 exclusivo para entrega de WM_HOTKEY."""
        # Força a inicialização da fila de mensagens para a thread
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        self._thread_id = kernel32.GetCurrentThreadId()

        registered_ids = []
        for hk_id, combo, _ in hotkeys:
            mod, vk = parse_hotkey(combo)
            if vk != 0:
                ok = user32.RegisterHotKey(None, hk_id, mod, vk)
                if ok:
                    registered_ids.append(hk_id)
                else:
                    err = ctypes.GetLastError()
                    print(f"⚠️ Não foi possível registrar hotkey '{combo}': Código {err}")

        ready_event.set()

        try:
            while self._running:
                res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res <= 0:
                    break
                if msg.message == WM_HOTKEY:
                    hk_id = int(msg.wParam)
                    cb = self._callbacks.get(hk_id)
                    if cb:
                        try:
                            cb()
                        except Exception as e:
                            print(f"⚠️ Erro ao executar hotkey callback: {e}")
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            for hk_id in registered_ids:
                try:
                    user32.UnregisterHotKey(None, hk_id)
                except Exception:
                    pass

    def stop(self):
        """Finaliza a thread e desregistra os atalhos."""
        with self._lock:
            self._running = False
            if self._thread and self._thread.is_alive():
                if self._thread_id:
                    user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
                self._thread.join(timeout=0.5)
            self._thread = None
            self._thread_id = None
