import sys
import ctypes
from ctypes.wintypes import DWORD, ULONG

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState', DWORD),
        ('AccentFlags', DWORD),
        ('GradientColor', DWORD),
        ('AnimationId', DWORD)
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ('Attribute', DWORD),
        ('Data', ctypes.POINTER(ACCENT_POLICY)),
        ('SizeOfData', ULONG)
    ]

def apply_blur(hwnd, enable=True, hex_color="#00000000"):
    """
    Aplica o efeito Acrylic/Mica nativo do Windows 11/10 na janela.
    Requer que a janela tenha Qt::WA_TranslucentBackground ativado.
    """
    if sys.platform != 'win32':
        return
        
    try:
        HWND = int(hwnd)
        
        # Tenta aplicar Mica/Acrylic nativo do Windows 11 (DWM)
        try:
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            # 1 = Default, 2 = Mica, 3 = Acrylic, 4 = Mica Alt
            backdrop_type = ctypes.c_int(3 if enable else 1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                HWND, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type)
            )
            
            # Forçar cantos arredondados bonitos no W11
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            corner = ctypes.c_int(DWMWCP_ROUND if enable else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                HWND, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner), ctypes.sizeof(corner)
            )
        except Exception:
            pass # Pode falhar se for W10 antigo
            
        # Fallback para SetWindowCompositionAttribute (Windows 10/11)
        accent = ACCENT_POLICY()
        # 3 = Blur, 4 = Acrylic
        accent.AccentState = 4 if enable else 0
        accent.AccentFlags = 2 # Ativa a cor de gradiente
        
        if hex_color.startswith('#'):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                hex_color += '00'
            if len(hex_color) == 8:
                # Padrão W11 DWM para ABGR
                r, g, b, a = hex_color[0:2], hex_color[2:4], hex_color[4:6], hex_color[6:8]
                abgr = f"{a}{b}{g}{r}"
                accent.GradientColor = int(abgr, 16)
        
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.SizeOfData = ctypes.sizeof(accent)
        data.Data = ctypes.pointer(accent)
        
        ctypes.windll.user32.SetWindowCompositionAttribute(HWND, ctypes.byref(data))
    except Exception as e:
        print(f"Aviso: Não foi possível aplicar Glassmorphism nativo no SO ({e})")
