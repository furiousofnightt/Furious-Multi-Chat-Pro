import sys
import ctypes

def apply_blur(hwnd, enable=True, hex_color="#121212AA"):
    """
    Aplica cantos arredondados e modo escuro nativo no Windows 11/10 via DWMAPI oficial.
    A transparência fumê/translúcida no Windows 10 e 11 é gerenciada com 100% de
    fidelidade visual diretamente pelo canal alfa do PyQt6 (Qt::WA_TranslucentBackground),
    sem chamar APIs não documentadas da user32 (evitando falsos positivos de antivírus).
    """
    if sys.platform != 'win32':
        return
        
    try:
        HWND = int(hwnd)
        
        # 1. Ativar Immersive Dark Mode no DWM (evita qualquer moldura ou borda clara)
        # Atributo 20 = Windows 11 / Windows 10 build recente, Atributo 19 = Windows 10 1809
        for attr in (20, 19):
            try:
                dark_mode = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    HWND, attr, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode)
                )
            except Exception:
                pass

        # 2. Se for Windows 11, aplicar cantos arredondados e desativar backdrop leitoso
        try:
            is_win11 = sys.getwindowsversion().build >= 22000
        except Exception:
            is_win11 = False

        if is_win11:
            try:
                # 1 = DWMSBT_NONE: Remove a névoa esbranquiçada/leitosa do DWM,
                # permitindo que o fundo fumê do Qt apareça com nitidez e cores exatas
                DWMWA_SYSTEMBACKDROP_TYPE = 38
                backdrop_type = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    HWND, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type)
                )
                
                # Cantos arredondados nativos do Windows 11
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = 2
                corner = ctypes.c_int(DWMWCP_ROUND if enable else 0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    HWND, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner), ctypes.sizeof(corner)
                )
            except Exception:
                pass

        # No Windows 10, a transparência translúcida escura é gerenciada
        # nativamente pelo PyQt6 (WA_TranslucentBackground + background-color: rgba(...)),
        # garantindo visual limpo sem ruído e sem disparar alertas de segurança.

    except Exception as e:
        print(f"Aviso: Não foi possível aplicar atributos visuais DWM ({e})")

