import sys
import signal
import os
import traceback

# Silenciar avisos internos de fontes e scripts raros do Qt (ex: tailandês/cirílico)
# DEVE ficar ANTES de qualquer import do PyQt6 para ter efeito
os.environ["QT_LOGGING_RULES"] = "qt.text.font.db.warning=false;qt.text.font.db.debug=false"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import QTimer, Qt

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Necessário ser definido ANTES de criar o QApplication para o WebEngine funcionar,
# mas sem carregar o Chromium no startup (carregamento lazy quando a janela de login abre)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from ui.main_window import ChatWindow
from ui.config_window import ConfigWindow
from core.settings_manager import SettingsManager
from core.chat_manager import ChatManager
from core.hotkey_manager import HotkeyManager
from utils.resource_path import resource_path

def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(f"💥 Erro crítico:\n{error_msg}")
    with open("crash_log.txt", "a") as f:
        f.write("\n" + "="*20 + "\n" + error_msg)
    sys.exit(1)

sys.excepthook = exception_hook

def load_custom_fonts():
    fonts_dir = resource_path(os.path.join("assets", "fonts"))
    if os.path.exists(fonts_dir):
        for font_file in os.listdir(fonts_dir):
            if font_file.endswith(".ttf"):
                path = os.path.join(fonts_dir, font_file)
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id == -1:
                    print(f"❌ Falha ao carregar fonte: {font_file}")
                else:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    print(f"✅ Fonte carregada: {font_file} ({', '.join(families)})")

def main():
    # Permitir Ctrl+C no terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    load_custom_fonts()
    
    # Timer necessário para o Python processar sinais no Windows/Qt
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    
    settings = SettingsManager()
    window = ChatWindow(settings_manager=settings)
    if hasattr(window, 'viewers_page') and window.viewers_page:
        window.viewers_page._settings_manager = settings
        window.viewers_page.refresh_state()
    if hasattr(window, 'gifts_page') and window.gifts_page:
        window.gifts_page._settings_manager = settings
    chat_manager = ChatManager(settings, window)
    # Injeta referência do chat_manager na janela para que request_sync_viewers funcione
    window._chat_manager = chat_manager
    
    # --- HOTKEY MANAGER ---
    hotkey_manager = HotkeyManager(settings)
    
    def toggle_window_visibility():
        """Alterna visibilidade da janela mantendo o chat ativo no tray."""
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()
    
    hotkey_manager.toggle_visibility_requested.connect(toggle_window_visibility)
    hotkey_manager.clear_chat_requested.connect(window.clear_chat)
    hotkey_manager.toggle_tts_requested.connect(window.toggle_tts)
    hotkey_manager.toggle_clickthrough_requested.connect(window.toggle_clickthrough)
    hotkey_manager.start()
    
    hk_vis = settings.settings.get('hotkey_toggle_visibility','ctrl+shift+h')
    hk_clear = settings.settings.get('hotkey_clear_chat','ctrl+shift+c')
    hk_tts = settings.settings.get('hotkey_toggle_tts','ctrl+m')
    hk_clickthrough = settings.settings.get('hotkey_clickthrough','ctrl+alt+t')
    print(f"⌨️ Hotkeys ativas: Mostrar/Esconder={hk_vis} | Limpar={hk_clear} | Voz={hk_tts} | Click-Through={hk_clickthrough}")
    # ----------------------
    
    def open_config():
        old_twitch = settings.settings.get("twitch", "")
        old_tiktok = settings.settings.get("tiktok", "")
        old_kick = settings.settings.get("kick", "")
        old_youtube = settings.settings.get("youtube", "")
        old_lang = settings.settings.get("language", "pt-br")
        
        config_ui = ConfigWindow(settings, window, chat_manager)
        if config_ui.exec():
            # Sempre avalia mudanças visuais em tempo real sem precisar reconectar chat
            window.apply_theme(settings.settings)
            if hasattr(window, 'viewers_page') and window.viewers_page:
                window.viewers_page.refresh_state()
            
            # Re-registra hotkeys com as novas combinações salvas
            hotkey_manager.start()
            
            # Reconecta APENAS se algum nome de streamer tiver sofrido alteração OU idioma mudou
            new_twitch = settings.settings.get("twitch", "")
            new_tiktok = settings.settings.get("tiktok", "")
            new_kick = settings.settings.get("kick", "")
            new_youtube = settings.settings.get("youtube", "")
            new_lang = settings.settings.get("language", "pt-br")
            
            if old_lang != new_lang:
                chat_manager.restart_all()
            else:
                if old_twitch != new_twitch:
                    chat_manager.restart_platform("twitch")
                if old_tiktok != new_tiktok:
                    chat_manager.restart_platform("tiktok")
                if old_kick != new_kick:
                    chat_manager.restart_platform("kick")
                if old_youtube != new_youtube:
                    chat_manager.restart_platform("youtube")
    
    window.settings_requested.connect(open_config)
    # Aplicar configurações iniciais ANTES de mostrar
    window.apply_theme(settings.settings)
    
    # Sincroniza o botão de Fixar com o setting salvo
    is_pinned = settings.settings.get("always_on_top", True)
    window.pin_btn.setChecked(is_pinned)
    window.toggle_pin() # O toggle_pin já faz o show() final
    
    # Iniciar os motores do chat
    chat_manager.start_all()
    
    # Garantir encerramento total ao fechar
    app.aboutToQuit.connect(lambda: chat_manager.stop_all(total_stop=True))
    app.aboutToQuit.connect(hotkey_manager.stop)
    
    import os
    # Rodar o App
    exit_code = app.exec()
    
    # Encerramento imediato
    chat_manager.stop_all()
    hotkey_manager.stop()
    os._exit(exit_code)

if __name__ == "__main__":
    main()
