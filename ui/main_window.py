import os
import time
import html
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect, QTimer, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QMenu,
    QLineEdit, QHBoxLayout, QPushButton,
    QApplication, QSystemTrayIcon, QStackedWidget
)
from PyQt6.QtGui import QAction, QIcon
from utils.blur_window import apply_blur
from utils.translations import get_translation
from utils.resource_path import resource_path
from utils.tts_engine import TTSManager
from ui.widgets import (
    ChatPageWidget,
    OnlineViewersListWidget,
    LiveGiftsListWidget,
)


class ChatWindow(QMainWindow):
    settings_requested = pyqtSignal()
    command_executed = pyqtSignal(str)
    RESIZE_MARGIN = 8  # Margem para redimensionar em pixels

    def __init__(self, settings_manager=None):
        super().__init__()
        self.settings_manager = settings_manager
        self.setMouseTracking(True)
        self.init_ui()
        self._drag_pos = QPoint()
        self._auto_scroll = True   # Auto-scroll ativado por padrão
        self._user_scrolled = False # True = usuário subiu o chat manualmente
        self.tts_manager = TTSManager(parent=self)
        if hasattr(self, 'chat_page'):
            self.chat_page.tts_manager = self.tts_manager
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Seta o ícone da janela (Ico para Windows)
        icon_path = resource_path("assets/icone.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback para PNG se o ICO sumir
            png_path = resource_path("assets/icone.png")
            if os.path.exists(png_path):
                self.setWindowIcon(QIcon(png_path))

        self.tray_icon = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_tray()
        
        # Iniciar no topo se configurado
        if self._pinned:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self.show()

    def set_click_through(self, enabled):
        if enabled:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTransparentForInput)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowTransparentForInput)
        
        # É necessário mostrar a janela novamente após mudar flags
        self.show()

    def toggle_clickthrough(self):
        is_transparent = bool(self.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        new_state = not is_transparent
        self.set_click_through(new_state)
        
        # Opcional: salvar a preferência no settings se desejar, mas como é modo jogo, pode ser temporário
        if hasattr(self, 'settings_manager'):
            self.settings_manager.settings['click_through'] = new_state
            self.settings_manager.save_settings()
            
        status = "Ativado (Mouse ignora o chat)" if new_state else "Desativado (Mouse interage com o chat)"
        icon = "ghost-green.svg" if new_state else "ghost-red.svg"
        
        # Usa um try pra evitar erro se add_message não existir na hora do startup
        try:
            self.add_message("Sistema", f"<img src='{icon}'> Modo Fantasma {status}!", "system")
        except AttributeError:
            pass

    def keyPressEvent(self, event):
        # Atalho '/' para abrir comandos
        if event.key() == Qt.Key.Key_Slash:
            self.command_input.show()
            self.command_input.setFocus()
        # Esc para fechar comando ou configurações
        elif event.key() == Qt.Key.Key_Escape:
            self.command_input.hide()
        # Atalho Ctrl + Alt + S para abrir configurações (Failsafe para Click-Through)
        elif event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier) and event.key() == Qt.Key.Key_S:
            self.settings_requested.emit()
        # Atalho Ctrl + Q para sair
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Q:
            self.close()

    def show_context_menu(self, pos):
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #555; }
        """)
        
        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
        settings_action = QAction(get_translation("menu_settings", lang), self)
        settings_action.triggered.connect(self.settings_requested.emit)
        
        clear_action = QAction(get_translation("menu_clear_chat", lang), self)
        clear_action.triggered.connect(self.clear_chat)
        
        exit_action = QAction(get_translation("menu_exit", lang), self)
        exit_action.triggered.connect(self.close)
        
        context_menu.addAction(settings_action)
        context_menu.addAction(clear_action)
        context_menu.addSeparator()
        context_menu.addAction(exit_action)
        context_menu.exec(self.mapToGlobal(pos))

    def clear_chat(self):
        if hasattr(self, 'chat_page'):
            self.chat_page.clear_chat()
            lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
            label = get_translation("system_label", lang)
            msg = get_translation("chat_cleared", lang)
            self.add_message(label, msg, "system")
            return


    def toggle_tts(self):
        if hasattr(self, 'tts_manager'):
            is_muted = self.tts_manager.toggle_mute()
            lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
            status = get_translation("bot_voice_disabled", lang) if is_muted else get_translation("bot_voice_enabled", lang)
            self.add_message(get_translation("system_label", lang), f"🔊 {get_translation('bot_voice_status', lang, status=status)}", "system")

    def setup_tray(self):
        """ Configura o ícone na bandeja do sistema (Tray) """
        icon_path = resource_path("assets/icone.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("assets/icone.png")
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("Furious Multi Chat Pro")
        
        # Menu do Tray
        tray_menu = QMenu()
        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
        
        show_action = QAction(QIcon(resource_path("assets/show.svg")), get_translation("tray_show_chat", lang), self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)
        
        clear_action = QAction(QIcon(resource_path("assets/clear.svg")), get_translation("tray_clear_chat", lang), self)
        clear_action.triggered.connect(self.clear_chat)
        tray_menu.addAction(clear_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction(QIcon(resource_path("assets/exit.svg")), get_translation("tray_quit_app", lang), self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def format_stat_number(self, num):
        """ Formata números grandes para formato abreviado (k, M, etc) conforme pedido do usuário """
        try:
            num = int(num)
            if num >= 1_000_000:
                val = num / 1_000_000
                return f"{val:.1f}M".replace('.0M', 'M')
            if num >= 1_000:
                val = num / 1_000
                return f"{val:.1f}k".replace('.0k', 'k')
            return str(num)
        except:
            return "0"

    def add_user_joined(self, username, platform):
        """Encaminha o usuário que entrou para o banner de notificações"""
        if hasattr(self, 'chat_page'):
            self.chat_page.add_user_joined(username, platform)
        elif hasattr(self, 'join_banner'):
            self.join_banner.add_user(username, platform)

    def clear_platform_joins(self, platform):
        """Limpa a fila de notificações pendentes de uma plataforma desconectada."""
        if hasattr(self, 'chat_page'):
            self.chat_page.clear_platform_joins(platform)
        elif hasattr(self, 'join_banner'):
            self.join_banner.clear_platform(platform)

    def reset_live_stats(self):
        """ Reseta todos os contadores da interface para o estado inicial """
        self._live_start_time = None
        self.viewers_lbl.setText("-")
        self.total_views_lbl.setText("-")
        self.uptime_lbl.setText("0:00:00")
        self.likes_lbl.setText("0")

    def update_live_stats(self, viewers, uptime_seconds, likes=0, total_views=0):
        try: viewers = int(viewers)
        except: viewers = 0
        try: uptime_seconds = int(uptime_seconds)
        except: uptime_seconds = 0
        try: likes = int(likes)
        except: likes = 0
        try: total_views = int(total_views)
        except: total_views = 0
        
        self.viewers_lbl.setText(self.format_stat_number(viewers) if viewers > 0 else "-")
            
        if total_views > 0 or self.total_views_lbl.text() == "-":
            self.total_views_lbl.setText(self.format_stat_number(total_views) if total_views > 0 else "-")
        
        # Atualiza curtidas
        self.likes_lbl.setText(self.format_stat_number(likes))
            
        import time
        # Sincroniza o relógio interno nativo com a fonte verdadeira via unix epoch
        if uptime_seconds > 0:
            self._live_start_time = time.time() - uptime_seconds
        elif self._live_start_time is None:
            # Failsafe para iniciar cronômetro do zero quando Twitch ou Kick se conectam sozinhos
            self._live_start_time = time.time()
            
        self._update_uptime_display()

    def update_secondary_viewers(self, platform_viewers: dict, platform_status: dict = None):
        if platform_status is None:
            platform_status = {}
            
        from utils.resource_path import resource_path
        import os
        
        # Preparar o caminho do SVG para uso no HTML do Qt
        eye_path = resource_path("assets/eye.svg").replace('\\', '/')
        eye_icon = f"<img src='file:///{eye_path}' width='12' height='12'>"
        
        ttk = platform_viewers.get("tiktok", 0)
        tw  = platform_viewers.get("twitch", 0)
        kk  = platform_viewers.get("kick", 0)
        yt  = platform_viewers.get("youtube", 0)
        
        is_ttk_connected = platform_status.get("tiktok", False)
        is_tw_connected = platform_status.get("twitch", False)
        is_kk_connected = platform_status.get("kick", False)
        is_yt_connected = platform_status.get("youtube", False)
        
        # Se for tudo vazio e offline, exibe o default
        if ttk == 0 and tw == 0 and kk == 0 and yt == 0 and not any([is_ttk_connected, is_tw_connected, is_kk_connected, is_yt_connected]):
            self.viewers_lbl.setToolTip(f"<html>{eye_icon} Views (Baseado na plataforma primária)</html>")
            return

        # HTML Formatted Tooltip
        html = [
            f"<html><div style='margin-bottom: 4px;'>{eye_icon} <b>Views</b></div>",
            "<table style='margin-top: 4px;' cellpadding='1' cellspacing='0'>"
        ]
        
        if not is_ttk_connected:
            html.append("<tr><td style='padding-right: 10px; color: #888;'>TikTok:</td><td style='color: #888;'>Offline</td></tr>")
        elif ttk > 0:
            html.append(f"<tr><td style='padding-right: 10px;'>TikTok:</td><td><b>{self.format_stat_number(ttk)}</b></td></tr>")
        else:
            html.append("<tr><td style='padding-right: 10px;'>TikTok:</td><td style='color: #00e6e6;'>0</td></tr>")
            
        if not is_tw_connected:
            html.append("<tr><td style='padding-right: 10px; color: #888;'>Twitch:</td><td style='color: #888;'>Offline</td></tr>")
        elif tw > 0:
            html.append(f"<tr><td style='padding-right: 10px;'>Twitch:</td><td><b>{self.format_stat_number(tw)}</b></td></tr>")
        else:
            html.append("<tr><td style='padding-right: 10px;'>Twitch:</td><td style='color: #a970ff;'>0</td></tr>")
            
        if not is_kk_connected:
            html.append("<tr><td style='padding-right: 10px; color: #888;'>Kick:</td><td style='color: #888;'>Offline</td></tr>")
        elif kk > 0:
            html.append(f"<tr><td style='padding-right: 10px;'>Kick:</td><td><b>{self.format_stat_number(kk)}</b></td></tr>")
        else:
            html.append("<tr><td style='padding-right: 10px;'>Kick:</td><td style='color: #53fc18;'>0</td></tr>")

        if not is_yt_connected:
            html.append("<tr><td style='padding-right: 10px; color: #888;'>YouTube:</td><td style='color: #888;'>Offline</td></tr>")
        elif yt > 0:
            html.append(f"<tr><td style='padding-right: 10px;'>YouTube:</td><td><b>{self.format_stat_number(yt)}</b></td></tr>")
        else:
            html.append("<tr><td style='padding-right: 10px;'>YouTube:</td><td style='color: #ff0000;'>0</td></tr>")
        
        html.append("</table></html>")
        
        self.viewers_lbl.setToolTip("".join(html))

    def _force_show_viewers_tooltip(self):
        from PyQt6.QtWidgets import QToolTip
        from PyQt6.QtGui import QCursor
        QToolTip.showText(QCursor.pos(), self.viewers_lbl.toolTip(), self.viewers_lbl)

    def _update_uptime_display(self):
        if not self._live_start_time:
            return
            
        import time
        current_uptime = int(time.time() - self._live_start_time)
        if current_uptime < 0:
            current_uptime = 0
            
        hrs = current_uptime // 3600
        mins = (current_uptime % 3600) // 60
        secs = current_uptime % 60
        
        self.uptime_lbl.setText(f"{hrs:d}:{mins:02d}:{secs:02d}")

    def quick_exit(self):
        from PyQt6.QtWidgets import QMessageBox, QApplication
        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
        reply = QMessageBox.question(self, get_translation("confirm_quit_title", lang), 
            get_translation("confirm_quit_msg", lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

    def closeEvent(self, event):
        """ Sobrescreve o fechar para minimizar para a tray opcionalmente """
        # Por enquanto, vamos apenas minimizar se o usuário fechar pelo 'X' 
        # mas permitir fechar totalmente pelo menu do Tray
        if self.tray_icon.isVisible():
            self.hide()
            lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
            self.tray_icon.showMessage(
                "Furious Multi Chat Pro",
                get_translation("tray_running_bg", lang),
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()

    def init_ui(self):
        # Janela sem bordas e com fundo transparente
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resize(400, 600)
        
        # Central Widget
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setCentralWidget(self.central_widget)
        
        # Monitorar eventos de redimensionamento globalmente na janela
        self.central_widget.setMouseTracking(True)
        self.central_widget.installEventFilter(self)

        # Header (Barra de Título Customizada)
        self.header = QWidget()
        self.header.setFixedHeight(55)
        self.header.setStyleSheet("""
            QWidget {
                background-color: #222;
                border-bottom: 2px solid #444;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 10, 0)


        # VBox para organizar o Título em cima e as Estatísticas em baixo
        title_vbox = QVBoxLayout()
        title_vbox.setContentsMargins(0, 5, 0, 5) # Pequena margem superior e inferior
        title_vbox.setSpacing(1) # Perto um do outro
        
        self.title_label = QLabel("Furious Multi Chat Pro")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        title_vbox.addWidget(self.title_label)

        # Contador de Status (Viewers e Uptime) logo abaixo do título
        self.stats_container = QWidget()
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(10)
        
        lang = self.settings_manager.settings.get("language", "pt-br") if (getattr(self, "settings_manager", None) and hasattr(self.settings_manager, "settings")) else "pt-br"

        self.viewers_lbl = QPushButton("-")
        self.viewers_lbl.setIcon(QIcon(resource_path("assets/eye.svg")))
        self.viewers_lbl.setIconSize(QSize(14, 14)) # Ícone um pouco menor
        self.viewers_lbl.setToolTip(get_translation("tooltip_views_primary", lang))
        self.viewers_lbl.setStyleSheet("color: #00e6e6; font-size: 12px; font-weight: bold; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.viewers_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.viewers_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.viewers_lbl.clicked.connect(self._force_show_viewers_tooltip)
        
        self.total_views_lbl = QPushButton("-")
        self.total_views_lbl.setIcon(QIcon(resource_path("assets/users.svg")))
        self.total_views_lbl.setIconSize(QSize(14, 14))
        self.total_views_lbl.setToolTip(get_translation("tooltip_total_views_ttk", lang))
        self.total_views_lbl.setStyleSheet("color: #00e6e6; font-size: 12px; font-weight: bold; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.total_views_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.uptime_lbl = QPushButton("0:00:00")
        self.uptime_lbl.setIcon(QIcon(resource_path("assets/clock.svg")))
        self.uptime_lbl.setIconSize(QSize(14, 14))
        self.uptime_lbl.setToolTip(get_translation("tooltip_uptime", lang))
        self.uptime_lbl.setStyleSheet("color: #b3b3b3; font-size: 12px; font-weight: bold; font-family: 'Consolas', monospace; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.uptime_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.likes_lbl = QPushButton("0")
        self.likes_lbl.setIcon(QIcon(resource_path("assets/heart.svg")))
        self.likes_lbl.setIconSize(QSize(14, 14))
        self.likes_lbl.setToolTip(get_translation("tooltip_likes", lang))
        self.likes_lbl.setStyleSheet("color: #ff4d4d; font-size: 12px; font-weight: bold; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.likes_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        stats_layout.addWidget(self.viewers_lbl)
        stats_layout.addWidget(self.total_views_lbl)
        stats_layout.addWidget(self.uptime_lbl)
        stats_layout.addWidget(self.likes_lbl)
        stats_layout.addStretch() # Compacta os botões à esquerda
        
        title_vbox.addWidget(self.stats_container)
        title_vbox.addStretch()
        
        # Adiciona a pilha de título+stats no layout do cabeçalho
        header_layout.addLayout(title_vbox)

        # Spacer principal (empurra botões de controle para a direita)
        header_layout.addStretch()

        # Timer interno para o Uptime
        self._live_start_time = None
        self.uptime_timer = QTimer(self)
        self.uptime_timer.timeout.connect(self._update_uptime_display)
        self.uptime_timer.start(1000)

        # Botão Alternar Visualização (Chat <-> Espectadores Online)
        self.view_switch_btn = QPushButton()
        self.view_switch_btn.setFixedSize(30, 30)
        self.view_switch_btn.setToolTip(get_translation("tooltip_viewers_page", lang))
        self.view_switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_users = QIcon(resource_path("assets/users.svg"))
        if not icon_users.isNull():
            self.view_switch_btn.setIcon(icon_users)
            self.view_switch_btn.setIconSize(QSize(18, 18))
        self.view_switch_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(0, 230, 230, 35); border-radius: 5px; }
        """)
        self.view_switch_btn.clicked.connect(lambda: self.switch_view(1 if self.stacked_widget.currentIndex() != 1 else 0))
        header_layout.addWidget(self.view_switch_btn)

        # Botão Alternar Visualização (Chat <-> Presentes da Live)
        self.gifts_btn = QPushButton()
        self.gifts_btn.setFixedSize(30, 30)
        self.gifts_btn.setToolTip(get_translation("tooltip_gifts_page", lang))
        self.gifts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_gifts = QIcon(resource_path("assets/gift_tab.svg"))
        if not icon_gifts.isNull():
            self.gifts_btn.setIcon(icon_gifts)
            self.gifts_btn.setIconSize(QSize(18, 18))
        self.gifts_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 180, 0, 35); border-radius: 5px; }
        """)
        self.gifts_btn.clicked.connect(lambda: self.switch_view(2 if self.stacked_widget.currentIndex() != 2 else 0))
        header_layout.addWidget(self.gifts_btn)

        # Botão Configurações
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(30,30)
        self.settings_btn.setToolTip(get_translation("tooltip_settings", lang))
        icon_settings = QIcon(resource_path("assets/settings.svg"))
        self.settings_btn.setIcon(icon_settings)
        self.settings_btn.setIconSize(QSize(18, 18))
        self.settings_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 30); border-radius: 5px; }
        """)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        header_layout.addWidget(self.settings_btn)

        # Botão Sair Rápido (Portinha)
        self.exit_btn = QPushButton()
        self.exit_btn.setFixedSize(30, 30)
        self.exit_btn.setToolTip(get_translation("tooltip_exit_quick", lang))
        icon_exit = QIcon(resource_path("assets/exit.svg"))
        self.exit_btn.setIcon(icon_exit)
        self.exit_btn.setIconSize(QSize(18, 18))
        self.exit_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 102, 102, 30); border-radius: 5px; }
        """)
        self.exit_btn.clicked.connect(self.quick_exit)
        header_layout.addWidget(self.exit_btn)

        # Botão Fixar (Pin)
        self._pinned = True
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(30, 30)
        self.pin_btn.setToolTip(get_translation("tooltip_pin", lang))
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)
        icon_pin = QIcon(resource_path("assets/pin.svg"))
        self.pin_btn.setIcon(icon_pin)
        self.pin_btn.setIconSize(QSize(16, 16))
        self.pin_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 30); border-radius: 5px; }
            QPushButton:checked { background-color: rgba(46, 204, 113, 40); border-radius: 5px; }
            QPushButton:checked:hover { background-color: rgba(46, 204, 113, 60); border-radius: 5px; }
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # Botão Fechar
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setToolTip(get_translation("tooltip_close", lang))
        self.close_btn.setStyleSheet("""
            QPushButton { 
                background: transparent; color: white; border: none; font-size: 16px; 
            }
            QPushButton:hover { 
                background-color: #e81123; border-radius: 5px; 
            }
        """)
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)

        self.layout.addWidget(self.header)

        # ==========================================
        # STACKED WIDGET (Transição Suave de Telas)
        # ==========================================
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")

        # --- PÁGINA 0: CHAT GERAL (MODULARIZADO EM ui.widgets.ChatPageWidget) ---
        self.chat_page = ChatPageWidget(
            parent=self,
            settings_manager=getattr(self, 'settings_manager', None),
            tts_manager=getattr(self, 'tts_manager', None)
        )
        # Mantém referências diretas para compatibilidade retroativa total
        self.join_banner = self.chat_page.join_banner
        self.scroll_area = self.chat_page.scroll_area
        self.chat_container = self.chat_page.chat_container
        self.chat_layout = self.chat_page.chat_layout
        self.notification_container = self.chat_page.notification_container

        self.stacked_widget.addWidget(self.chat_page)

#

        # --- PÁGINA 1: ESPECTADORES ONLINE (TIKTOK) ---
        self.viewers_page = OnlineViewersListWidget(
            self,
            settings_manager=getattr(self, 'settings_manager', None)
        )
        self.viewers_page.back_requested.connect(lambda: self.switch_view(0))
        self.viewers_page.open_settings_requested.connect(self.settings_requested.emit)
        self.viewers_page.sync_requested.connect(self.request_sync_viewers)
        self.stacked_widget.addWidget(self.viewers_page)

        # --- PÁGINA 2: PRESENTES DA LIVE ---
        self.gifts_page = LiveGiftsListWidget(
            self,
            settings_manager=getattr(self, 'settings_manager', None)
        )
        self.gifts_page.back_requested.connect(lambda: self.switch_view(0))
        self.stacked_widget.addWidget(self.gifts_page)

        self.layout.addWidget(self.stacked_widget)

        # O container ganha estilo real no apply_theme()
        self.central_widget.setStyleSheet("""
            #central_widget {
                background-color: rgba(15, 15, 15, 180);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
            }
        """)

        # Configurações de janela executadas uma única vez após construir todos os widgets
        self._setup_window_once()

    def _setup_window_once(self):
        """Configurações de inicialização executadas apenas uma vez (mouse tracking,
        event filters, command input). Chamado pelo init_ui após construir todos os widgets."""
        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"

        # Input de Comandos (Oculto por padrão, criado uma única vez)
        if not hasattr(self, 'command_input'):
            self.command_input = QLineEdit()
            self.command_input.setPlaceholderText(get_translation("placeholder_command", lang))
            self.command_input.setStyleSheet("""
                QLineEdit { background: rgba(30, 30, 30, 180); color: white; border: 1px solid #555; padding: 5px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            """)
            self.command_input.hide()
            self.command_input.returnPressed.connect(self.process_command)
            self.layout.addWidget(self.command_input)

        # Ativar Mouse Tracking em todos os widgets relevantes
        self.setMouseTracking(True)
        self.central_widget.setMouseTracking(True)
        self.header.setMouseTracking(True)
        self.scroll_area.setMouseTracking(True)
        self.scroll_area.viewport().setMouseTracking(True)
        self.chat_container.setMouseTracking(True)
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setMouseTracking(True)
            self.chat_page.setMouseTracking(True)
            self.viewers_page.setMouseTracking(True)
            self.viewers_page.scroll_area.setMouseTracking(True)
            self.viewers_page.scroll_area.viewport().setMouseTracking(True)
            self.viewers_page.list_container.setMouseTracking(True)
            if hasattr(self, 'gifts_page'):
                self.gifts_page.setMouseTracking(True)
                self.gifts_page.scroll_area.setMouseTracking(True)
                self.gifts_page.scroll_area.viewport().setMouseTracking(True)
                self.gifts_page.list_container.setMouseTracking(True)

        self.RESIZE_MARGIN = 8
        self._resizing = False

        # Instalar Filtros de Evento para redimensionar mesmo sobre os filhos
        self.header.installEventFilter(self)
        self.scroll_area.installEventFilter(self)
        self.scroll_area.viewport().installEventFilter(self)
        self.chat_container.installEventFilter(self)
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.installEventFilter(self)
            self.chat_page.installEventFilter(self)
            self.viewers_page.installEventFilter(self)
            self.viewers_page.scroll_area.installEventFilter(self)
            self.viewers_page.scroll_area.viewport().installEventFilter(self)
            self.viewers_page.list_container.installEventFilter(self)
            if hasattr(self, 'gifts_page'):
                self.gifts_page.installEventFilter(self)
                self.gifts_page.scroll_area.installEventFilter(self)
                self.gifts_page.scroll_area.viewport().installEventFilter(self)
                self.gifts_page.list_container.installEventFilter(self)

        # Mensagem inicial de sistema (apenas uma vez)
        self.add_message(get_translation("system_label", lang), get_translation("system_initialized", lang), "system")
        # Marca que o setup inicial foi concluído; apply_theme usará essa flag
        # para saber se deve postar mensagem nas chamadas subsequentes (salvar config)
        self._window_setup_done = True


    def apply_theme(self, settings_dict):
        """ Aplica configurações visuais: Opacidade do Fundo, Opacidade de Texto e Blur do Windows.
        Otimizado para não travar o chat ao alterar opacidade — só repinta quando o valor muda. """
        glass_enabled = settings_dict.get("glassmorphism", True)

        # Opacidade do fundo: padrão 75% (0.75) caso não configurado
        bg_opacity = settings_dict.get("bg_opacity", settings_dict.get("opacity", 0.75))
        try:
            bg_opacity = max(0.0, min(1.0, float(bg_opacity)))
        except (ValueError, TypeError):
            bg_opacity = 0.75

        # Opacidade específica dos textos/mensagens: padrão 100% (1.0)
        text_opacity = settings_dict.get("text_opacity", 1.0)
        try:
            text_opacity = max(0.1, min(1.0, float(text_opacity)))
        except (ValueError, TypeError):
            text_opacity = 1.0

        # Manter a janela no SO sempre em 1.0 (opaca) para que a transparência
        # seja puramente interna via canal alfa (WA_TranslucentBackground), garantindo
        # textos 100% nítidos e cantos arredondados perfeitos
        self.setWindowOpacity(1.0)

        bg_alpha = int(bg_opacity * 255)
        text_alpha = int(text_opacity * 255)

        # ── Fundo do #central_widget ─────────────────────────────────────────────
        # Só aplica o setStyleSheet (que força repaint de toda a árvore) se o valor
        # realmente mudou, evitando o freeze de 3-5s ao abrir config sem alterar nada.
        last_bg = getattr(self, '_last_bg_alpha', None)
        if last_bg != bg_alpha:
            self._last_bg_alpha = bg_alpha
            self.central_widget.setStyleSheet(f"""
                #central_widget {{
                    background-color: rgba(0, 0, 0, {bg_alpha});
                    border: 1px solid rgba(255, 255, 255, 25);
                    border-radius: 10px;
                }}
            """)

        # Garantir que a chat_page e stacked_widget sejam 100% transparentes
        if hasattr(self, 'chat_page'):
            self.chat_page.setGraphicsEffect(None)
            self.chat_page.setStyleSheet("background: transparent;")
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setStyleSheet("background: transparent;")

        # ── Opacidade de texto ───────────────────────────────────────────────────
        last_text = getattr(self, '_last_text_alpha', None)
        self.current_text_opacity = text_opacity
        if last_text != text_alpha:
            self._last_text_alpha = text_alpha
            if hasattr(self, 'chat_container'):
                self.chat_container.setStyleSheet(
                    f"background: transparent; QLabel {{ color: rgba(255, 255, 255, {text_alpha}); }}"
                )

        # ── apply_blur (DWM nativo) ──────────────────────────────────────────────
        # Diferido para o próximo ciclo do event loop: o Qt processa primeiro o
        # repaint do stylesheet acima, depois chama o DWM — sem bloquear o chat.
        hex_alpha = f"{min(255, max(10, bg_alpha)):02X}"
        last_glass = getattr(self, '_last_glass_enabled', None)
        if last_glass != glass_enabled or last_bg != bg_alpha:
            self._last_glass_enabled = glass_enabled
            _hex_color = f"#000000{hex_alpha}"
            QTimer.singleShot(0, lambda: apply_blur(self.winId(), enable=glass_enabled, hex_color=_hex_color))

        # ── Mensagem de confirmação ao salvar configurações ──────────────────────
        # _window_setup_done é setado em _setup_window_once (startup). Nas chamadas
        # subsequentes (salvar config), posta a mensagem de tema aplicado.
        if getattr(self, '_window_setup_done', False):
            lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
            self.add_message(get_translation("system_label", lang), get_translation("system_initialized", lang), "system")


    def switch_view(self, target_index=None):
        """Alterna instantaneamente entre Chat (0), Espectadores (1) e Presentes (2)."""
        if not hasattr(self, 'stacked_widget') or not self.stacked_widget:
            return

        current = self.stacked_widget.currentIndex()
        if target_index is None:
            target_index = 1 if current == 0 else 0

        if target_index == current:
            return

        self.stacked_widget.setCurrentIndex(target_index)

        lang = self.settings_manager.settings.get("language", "pt-br") if (getattr(self, "settings_manager", None) and hasattr(self.settings_manager, "settings")) else "pt-br"
        # Atualiza botões do header
        if target_index == 1:
            if hasattr(self, 'viewers_page') and self.viewers_page:
                self.viewers_page.refresh_state()
            # Sincroniza automaticamente ao abrir a aba para carregar na hora sem precisar apertar o botão
            self.request_sync_viewers()
            self.view_switch_btn.setToolTip(get_translation("tooltip_chat_page", lang))
            self.view_switch_btn.setStyleSheet("""
                QPushButton { background-color: rgba(0, 230, 230, 45); border: 1px solid #00e6e6; border-radius: 5px; }
                QPushButton:hover { background-color: rgba(0, 230, 230, 75); }
            """)
            if hasattr(self, 'gifts_btn'):
                self.gifts_btn.setToolTip(get_translation("tooltip_gifts_page", lang))
                self.gifts_btn.setStyleSheet("""
                    QPushButton { background: transparent; border: none; }
                    QPushButton:hover { background-color: rgba(255, 180, 0, 35); border-radius: 5px; }
                """)
        elif target_index == 2:
            self._unread_gifts = 0
            if hasattr(self, 'gifts_btn'):
                self.gifts_btn.setToolTip(get_translation("tooltip_chat_page", lang))
                self.gifts_btn.setStyleSheet("""
                    QPushButton { background-color: rgba(255, 180, 0, 45); border: 1px solid #ffb400; border-radius: 5px; }
                    QPushButton:hover { background-color: rgba(255, 180, 0, 75); }
                """)
            self.view_switch_btn.setToolTip(get_translation("tooltip_viewers_page", lang))
            self.view_switch_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; }
                QPushButton:hover { background-color: rgba(0, 230, 230, 35); border-radius: 5px; }
            """)
        else:
            self.view_switch_btn.setToolTip(get_translation("tooltip_viewers_page", lang))
            self.view_switch_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; }
                QPushButton:hover { background-color: rgba(0, 230, 230, 35); border-radius: 5px; }
            """)
            if hasattr(self, 'gifts_btn'):
                self.gifts_btn.setToolTip(get_translation("tooltip_gifts_page", lang))
                if getattr(self, '_unread_gifts', 0) > 0:
                    self.gifts_btn.setStyleSheet("""
                        QPushButton { background-color: rgba(255, 180, 0, 25); border: 1px dashed rgba(255, 180, 0, 180); border-radius: 5px; }
                        QPushButton:hover { background-color: rgba(255, 180, 0, 50); }
                    """)
                else:
                    self.gifts_btn.setStyleSheet("""
                        QPushButton { background: transparent; border: none; }
                        QPushButton:hover { background-color: rgba(255, 180, 0, 35); border-radius: 5px; }
                    """)

    def add_gift(self, gift_data):
        """Adiciona um presente à aba de presentes e notifica visualmente se estiver em outra aba."""
        print(f"[Presentes] 🪟 add_gift chamado: {gift_data.get('gift_name')} de {gift_data.get('user')}", flush=True)
        if hasattr(self, 'gifts_page') and self.gifts_page:
            self.gifts_page.add_gift(gift_data)

        if hasattr(self, 'stacked_widget') and self.stacked_widget.currentIndex() != 2:
            self._unread_gifts = getattr(self, '_unread_gifts', 0) + 1
            if hasattr(self, 'gifts_btn'):
                self.gifts_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 180, 0, 35);
                        border: 1px solid rgba(255, 200, 50, 220);
                        border-radius: 5px;
                    }
                    QPushButton:hover { background-color: rgba(255, 180, 0, 60); }
                """)

    def clear_gifts(self):
        """Limpa a lista de presentes da aba."""
        if hasattr(self, 'gifts_page') and self.gifts_page:
            self.gifts_page.clear_gifts()
        self._unread_gifts = 0
        if hasattr(self, 'gifts_btn') and hasattr(self, 'stacked_widget') and self.stacked_widget.currentIndex() != 2:
            self.gifts_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; }
                QPushButton:hover { background-color: rgba(255, 180, 0, 35); border-radius: 5px; }
            """)

    def update_tiktok_viewers(self, viewers_list):
        """Atualiza a lista de espectadores online do TikTok na interface."""
        if hasattr(self, 'viewers_page') and self.viewers_page:
            self.viewers_page.set_viewers(viewers_list)

    def clear_tiktok_viewers(self):
        """Limpa a lista de espectadores online do TikTok na interface."""
        if hasattr(self, 'viewers_page') and self.viewers_page:
            self.viewers_page.clear_viewers()

    def request_sync_viewers(self):
        """Chama request_sync_now no handler TikTok ativo para forçar atualização em tempo real sem cache.
        
        Chamado pelo botão 'Sincronizar' e automaticamente ao alternar para a aba de espectadores online.
        """
        from chat_handlers.tiktok_handler import TikTokHandler
        chat_manager = getattr(self, '_chat_manager', None)
        if chat_manager:
            for h in getattr(chat_manager, 'handlers', []):
                if isinstance(h, TikTokHandler) and getattr(h, 'is_running', False):
                    h.request_sync_now()
                    return

        print("[Espectadores] ⚠️ TikTok offline: não foi possível sincronizar.", flush=True)
        # Nenhum handler ativo: exibe estado correto da aba
        if hasattr(self, 'viewers_page') and self.viewers_page:
            self.viewers_page.refresh_state()
        
    def process_command(self):
        cmd = self.command_input.text().strip()
        if cmd:
            self.command_executed.emit(cmd)
            self.command_input.clear()
        self.command_input.hide()

    def toggle_pin(self):
        """ Quando fixado: janela NAO pode ser arrastada e fica sempre por cima. """
        self._pinned = self.pin_btn.isChecked()
        
        # Salva no settings_manager para persistir
        if hasattr(self, 'settings_manager'):
            self.settings_manager.settings["always_on_top"] = self._pinned
            self.settings_manager.save_settings()

        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
        flags = self.windowFlags()
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setToolTip(get_translation("tooltip_pinned", lang))
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setToolTip(get_translation("tooltip_unpinned", lang))
        
        # Garante que a janela continue sendo Frameless
        flags |= Qt.WindowType.FramelessWindowHint
        
        self.setWindowFlags(flags)
        
        # No Windows, mudar flags pode tirar o foco. show() e raise_() ajudam.
        self.show()
        self.raise_()
        self.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # O Qt cuida do widget com setWidgetResizable(True) nativamente.
        # Porém, para forçar o WordWrap a funcionar (sem esticar pro infinito na horizontal):
        vp_width = self.scroll_area.viewport().width()
        if vp_width > 0:
            self.chat_container.setFixedWidth(vp_width)
        
        # Avisa ao layout interno para recalcular a altura
        if self.chat_layout:
            self.chat_layout.invalidate()

    def handle_scroll_value_changed(self, value):
        vbar = self.scroll_area.verticalScrollBar()
        at_bottom = (value >= vbar.maximum() - 80)
        # Só religa o auto-scroll se o usuário chegou ao fundo
        if at_bottom:
            self._auto_scroll = True
            self._user_scrolled = False

    def handle_scroll_range_changed(self, min_val, max_val):
        if self._auto_scroll and not self._user_scrolled:
            self.scroll_area.verticalScrollBar().setValue(max_val)

    def _scroll_to_bottom(self):
        # Só rola se o usuário NÃO subiu o chat manualmente
        if self._auto_scroll and not self._user_scrolled:
            vbar = self.scroll_area.verticalScrollBar()
            vbar.setValue(vbar.maximum())

    def add_message(self, user, text, platform="twitch"):
        if hasattr(self, 'chat_page'):
            self.chat_page.current_text_opacity = getattr(self, 'current_text_opacity', 1.0)
            self.chat_page.add_message(user, text, platform)
            return

    def animate_message(self, widget):
        if hasattr(self, 'chat_page'):
            self.chat_page.animate_message(widget)
            return

    # Margem para redimensionar (pixels)
    def get_resize_direction(self, pos):
        """ Retorna a direção de redimensionamento baseada na posição do mouse com validação estrita """
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        m = self.RESIZE_MARGIN
        
        # SÓ reconhece se estiver EXATAMENTE dentro da faixa de pixels da borda interna
        lx = (0 <= x <= m)
        rx = (w - m <= x <= w)
        ty = (0 <= y <= m)
        by = (h - m <= y <= h)
        
        if lx and ty: return "TL"
        if rx and ty: return "TR"
        if lx and by: return "BL"
        if rx and by: return "BR"
        if lx: return "L"
        if rx: return "R"
        if ty: return "T"
        if by: return "B"
        return None

    # Redimensionamento e Arrastre agora gerenciados via eventFilter

    def eventFilter(self, obj, event):
        """ Captura eventos nos filhos para redimensionar ou arrastar """
        # SCROLL LOCK: Detecta scroll manual do usuário via roda do mouse
        if event.type() == event.Type.Wheel:
            delta = event.angleDelta().y()
            if delta > 0:
                # Usu\u00e1rio scrollou para CIMA: trava o auto-scroll
                self._user_scrolled = True
                self._auto_scroll = False
            # Se scrollou para baixo, deixa o valueChanged cuidar de religar
        
        if event.type() == event.Type.MouseMove:
            global_pos = event.globalPosition().toPoint()
            local_pos = self.mapFromGlobal(global_pos)
            
            # Se a janela estiver fixada, ignore lógica de resize/drag
            if self._pinned:
                if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                return False

            if self._resizing:
                self._handle_resize_logic(global_pos)
                return True
            if self._drag_pos:
                self.move(global_pos - self._drag_pos)
                return True
                
            direction = self.get_resize_direction(local_pos)
            if direction:
                self._update_cursor_by_direction(direction)
                return True
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                
        elif event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                # Se estiver fixada, não permite iniciar drag/resize
                if self._pinned:
                    return False

                global_pos = event.globalPosition().toPoint()
                local_pos = self.mapFromGlobal(global_pos)
                direction = self.get_resize_direction(local_pos)
                
                if direction:
                    self._resizing = True
                    self._resize_direction = direction
                    self._start_pos = global_pos
                    self._start_geometry = self.geometry()
                    return True
                else:
                    # Arrastar se clicar no Header
                    h_pos = self.header.mapFromGlobal(global_pos)
                    if self.header.rect().contains(h_pos):
                        # Ignorar se clicar nos botões do header
                        if not self.close_btn.rect().contains(self.close_btn.mapFromGlobal(global_pos)) and \
                           not self.settings_btn.rect().contains(self.settings_btn.mapFromGlobal(global_pos)) and \
                           not self.viewers_lbl.rect().contains(self.viewers_lbl.mapFromGlobal(global_pos)):
                            self._drag_pos = global_pos - self.frameGeometry().topLeft()
                            return True
                    
        elif event.type() == event.Type.MouseButtonRelease:
            if self._resizing or self._drag_pos:
                self._resizing = False
                self._drag_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return True
            
        return super().eventFilter(obj, event)

    def _handle_resize_logic(self, global_pos):
        diff = global_pos - self._start_pos
        new_geo = QRect(self._start_geometry)
        
        if "L" in self._resize_direction:
            new_geo.setLeft(self._start_geometry.left() + diff.x())
        if "R" in self._resize_direction:
            new_geo.setRight(self._start_geometry.right() + diff.x())
        if "T" in self._resize_direction:
            new_geo.setTop(self._start_geometry.top() + diff.y())
        if "B" in self._resize_direction:
            new_geo.setBottom(self._start_geometry.bottom() + diff.y())
        
        if new_geo.width() >= 200 and new_geo.height() >= 200:
            self.setGeometry(new_geo)

    def _update_cursor_by_direction(self, direction):
        if direction in ["L", "R"]: self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif direction in ["T", "B"]: self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif direction in ["TL", "BR"]: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif direction in ["TR", "BL"]: self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else: self.setCursor(Qt.CursorShape.ArrowCursor)
