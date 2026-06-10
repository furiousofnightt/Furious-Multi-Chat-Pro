from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QSize, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QScrollArea, QMenu, 
    QGraphicsOpacityEffect, QLineEdit, QHBoxLayout, QPushButton, 
    QSizePolicy, QApplication, QFrame, QSystemTrayIcon, QLayout, QLayoutItem, QWidgetItem
)
from PyQt6.QtGui import QColor, QPalette, QFont, QAction, QPixmap, QIcon, QMouseEvent, QMovie
import re
import html
import os
import sys
from collections import deque
from utils.blur_window import apply_blur
from utils.translations import get_translation
from utils.resource_path import resource_path
from utils.tts_engine import TTSManager


class JoinNotificationBanner(QFrame):
    """Banner que exibe notificações de entrada de usuários com fila e timer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = deque()
        self.is_showing = False
        
        self.setFixedHeight(30)
        self.setFixedWidth(380)
        self.setStyleSheet("""
            JoinNotificationBanner {
                background-color: rgba(0, 230, 230, 90);
                border: 1px solid rgba(0, 230, 230, 180);
                border-radius: 15px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        
        layout.addStretch() # Espaço à esquerda
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(18, 18)
        self.icon_lbl.setScaledContents(True)
        icon_join = QIcon(resource_path("assets/join.svg"))
        if not icon_join.isNull():
            self.icon_lbl.setPixmap(icon_join.pixmap(18, 18))
        else:
            self.icon_lbl.setText("🚪") # Fallback
        self.icon_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon_lbl)
        
        self.text_lbl = QLabel("")
        self.text_lbl.setTextFormat(Qt.TextFormat.RichText)
        text_font = QFont()
        text_font.setBold(True)
        text_font.setPointSize(12)
        self.text_lbl.setFont(text_font)
        self.text_lbl.setStyleSheet("color: white; font-weight: 900; background: transparent;")
        layout.addWidget(self.text_lbl)
        
        layout.addStretch() # Espaço à direita
        
        # Efeito de opacidade para animações
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.process_queue)
        
        self.hide()

    def add_user(self, username, platform):
        # Evita duplicidade imediata na fila
        if any(u == username for u, p in self.queue):
            return
        self.queue.append((username, platform))
        if not self.is_showing:
            self.process_queue()

    def process_queue(self):
        if not self.queue:
            self.fade_out()
            return
            
        self.is_showing = True
        user, plat = self.queue.popleft()
        
        # Tenta pegar idioma do Main ou usar fallback
        lang = "pt-br"
        curr = self.parent()
        try:
            while curr:
                if hasattr(curr, 'settings_manager') and curr.settings_manager:
                    lang = curr.settings_manager.settings.get("language", "pt-br")
                    break
                curr = curr.parent()
        except: pass
        
        msg = get_translation("user_joined", lang, user)
        
        # Ajuste dinâmico de tamanho para caber no banner (380px total, ~320px texto)
        max_text_width = 310
        current_size = 12
        text_font = self.text_lbl.font()
        text_font.setPointSize(current_size)
        text_font.setBold(True)
        
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(text_font)
        
        # Diminuir até 8px se necessário
        while metrics.horizontalAdvance(msg) > max_text_width and current_size > 8:
            current_size -= 1
            text_font.setPointSize(current_size)
            metrics = QFontMetrics(text_font)
            
        self.text_lbl.setFont(text_font)
        self.text_lbl.setText(msg)
        
        # Já está sempre visível agora por design fixo
        # if self.parent() and isinstance(self.parent(), QWidget):
        #     self.parent().show()
            
        self.show()
        self.fade_in()
        
        # Exibe por 3.5 segundos e tenta o próximo (500ms fade + 3000ms stay)
        self.timer.start(3500)

    def fade_in(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.start()

    def fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.finished.connect(self._on_fade_out_finished)
        self.anim.start()

    def _on_fade_out_finished(self):
        self.is_showing = False
        self.hide()
        
        # Não oculta mais o pai para manter o layout fixo e estável
        # if self.parent() and isinstance(self.parent(), QWidget):
        #     self.parent().hide()
            
        if self.queue:
            self.process_queue()



class FlowLayout(QLayout):
    """Layout que organiza os elementos em linhas que quebram conforme o espaço disponível."""
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.items = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        line_height = 0
        
        for item in self.items:
            wid = item.widget()
            space_x = self.spacing()
            space_y = self.spacing()
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() - m.right() and line_height > 0:
                x = rect.x() + m.left()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
            
        return y + line_height - rect.y() + m.bottom()

class HeightAwareWidget(QWidget):
    """ Widget helper that natively calculates true pixel height based on varying widths. """
    def __init__(self, parent=None):
        super().__init__(parent)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        if self.layout():
            return self.layout().heightForWidth(width)
        return super().heightForWidth(width)
        
class ChatWindow(QMainWindow):
    settings_requested = pyqtSignal()
    command_executed = pyqtSignal(str)
    RESIZE_MARGIN = 8  # Margem para redimensionar em pixels

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.init_ui()
        self._drag_pos = QPoint()
        self._auto_scroll = True   # Auto-scroll ativado por padrão
        self._user_scrolled = False # True = usuário subiu o chat manualmente
        self.tts_manager = TTSManager(parent=self)
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
        
        settings_action = QAction("Configurações", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        
        clear_action = QAction("Limpar Chat", self)
        clear_action.triggered.connect(self.clear_chat)
        
        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(self.close)
        
        context_menu.addAction(settings_action)
        context_menu.addAction(clear_action)
        context_menu.addSeparator()
        context_menu.addAction(exit_action)
        context_menu.exec(self.mapToGlobal(pos))

    def clear_chat(self):
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
        label = get_translation("system_label", lang)
        msg = get_translation("chat_cleared", lang)
        self.add_message(label, msg, "system")

    def toggle_tts(self):
        if hasattr(self, 'tts_manager'):
            is_muted = self.tts_manager.toggle_mute()
            status = "Desativada" if is_muted else "Ativada"
            self.add_message("Sistema", f"🔊 Voz do Bot {status}!", "system")

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
        
        show_action = QAction(QIcon(resource_path("assets/show.svg")), "Mostrar Chat", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)
        
        clear_action = QAction(QIcon(resource_path("assets/clear.svg")), "Limpar Chat", self)
        clear_action.triggered.connect(self.clear_chat)
        tray_menu.addAction(clear_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction(QIcon(resource_path("assets/exit.svg")), "Fechar App Completamente", self)
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
        if hasattr(self, 'join_banner'):
            self.join_banner.add_user(username, platform)

    def reset_live_stats(self):
        """ Reseta todos os contadores da interface para o estado inicial """
        self._live_start_time = None
        self.viewers_lbl.setText("-")
        self.uptime_lbl.setText("0:00:00")
        self.likes_lbl.setText("0")

    def update_live_stats(self, viewers, uptime_seconds, likes=0):
        try: viewers = int(viewers)
        except: viewers = 0
        try: uptime_seconds = int(uptime_seconds)
        except: uptime_seconds = 0
        try: likes = int(likes)
        except: likes = 0
        
        if viewers > 0 or self.viewers_lbl.text() == "-":
            self.viewers_lbl.setText(self.format_stat_number(viewers) if viewers > 0 else "-")
        
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
        reply = QMessageBox.question(self, 'Encerrar App', 
            "Deseja realmente encerrar o aplicativo completamente?",
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
            self.tray_icon.showMessage(
                "Furious Multi Chat Pro",
                "O chat continua rodando em segundo plano.",
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

        # Ícone no Header
        self.header_icon = QLabel()
        self.header_icon.setFixedSize(20, 20)
        self.header_icon.setStyleSheet("border: none; background: transparent;")
        icon_path = resource_path("assets/icone.ico")
        if os.path.exists(icon_path):
            self.header_icon.setPixmap(QIcon(icon_path).pixmap(20, 20))
        header_layout.addWidget(self.header_icon)

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
        
        self.viewers_lbl = QPushButton("-")
        self.viewers_lbl.setIcon(QIcon(resource_path("assets/eye.svg")))
        self.viewers_lbl.setIconSize(QSize(14, 14)) # Ícone um pouco menor
        self.viewers_lbl.setToolTip("Espectadores ao vivo. (Baseado na plataforma primária)")
        self.viewers_lbl.setStyleSheet("color: #00e6e6; font-size: 12px; font-weight: bold; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.viewers_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.uptime_lbl = QPushButton("0:00:00")
        self.uptime_lbl.setIcon(QIcon(resource_path("assets/clock.svg")))
        self.uptime_lbl.setIconSize(QSize(14, 14))
        self.uptime_lbl.setToolTip("Tempo de Live")
        self.uptime_lbl.setStyleSheet("color: #b3b3b3; font-size: 12px; font-weight: bold; font-family: 'Consolas', monospace; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.uptime_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.likes_lbl = QPushButton("0")
        self.likes_lbl.setIcon(QIcon(resource_path("assets/heart.svg")))
        self.likes_lbl.setIconSize(QSize(14, 14))
        self.likes_lbl.setToolTip("Total de curtidas (Corações)")
        self.likes_lbl.setStyleSheet("color: #ff4d4d; font-size: 12px; font-weight: bold; background: transparent; padding-top: 0px; border: none; text-align: left;")
        self.likes_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        stats_layout.addWidget(self.viewers_lbl)
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

        # Botão Configurações
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(30,30)
        self.settings_btn.setToolTip("Configurações (Ctrl+Alt+S)")
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
        self.exit_btn.setToolTip("Sair do Aplicativo Completamente")
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
        self.pin_btn.setToolTip("Fixar janela por cima")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)
        icon_pin = QIcon(resource_path("assets/pin.svg"))
        self.pin_btn.setIcon(icon_pin)
        self.pin_btn.setIconSize(QSize(16, 16))
        self.pin_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 30); border-radius: 5px; }
            QPushButton:checked { background-color: rgba(255, 215, 0, 40); border-radius: 5px; }
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # Botão Minimizar
        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(30, 30)
        self.min_btn.setToolTip("Minimizar janela")
        self.min_btn.setStyleSheet("""
            QPushButton { 
                background: transparent; color: white; border: none; font-size: 14px; 
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 30); border-radius: 5px; 
            }
        """)
        self.min_btn.clicked.connect(self.showMinimized)
        header_layout.addWidget(self.min_btn)

        # Botão Fechar
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
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

        # Banner de Notificação de Entrada (Fixo para não quebrar o Scroll)
        self.notification_container = QWidget()
        self.notification_container.setFixedHeight(45) # Altura fixa reservada
        notification_layout = QHBoxLayout(self.notification_container)
        notification_layout.setContentsMargins(0, 5, 0, 5)
        notification_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.join_banner = JoinNotificationBanner(self)
        notification_layout.addWidget(self.join_banner)
        self.layout.addWidget(self.notification_container)
        
        # Área de Scroll para as mensagens
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Framework UI fluida ligada
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 50);
                width: 5px;
                margin: 0px 0px 0px 0px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 100);
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
        """)
        
        self.chat_container = HeightAwareWidget()
        self.chat_container.setStyleSheet("background: transparent;")  # Sem fundo escuro
        self.chat_layout = QVBoxLayout(self.chat_container)
        
        # Alinha tudo pelo topo blindado agora que a altura exata está protegida no HeightAwareWidget
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setContentsMargins(10, 5, 25, 5)
        self.chat_layout.setSpacing(15) # 15px de espaço entre mensagens
        
        self.scroll_area.setWidget(self.chat_container)
        
        # Scroll automático via range changed
        vbar = self.scroll_area.verticalScrollBar()
        vbar.valueChanged.connect(self.handle_scroll_value_changed)
        
        self.layout.addWidget(self.scroll_area)
        
        # O container ganha estilo real no apply_theme()
        self.central_widget.setStyleSheet("""
            #central_widget {
                background-color: rgba(15, 15, 15, 180);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
            }
        """)

    def apply_theme(self, settings_dict):
        """ Aplica configurações visuais: Opacidade e Blur do Windows """
        # Fundo normal = 200, Fundo Glass = 1 (quase zero) para ver o Blur
        glass_enabled = settings_dict.get("glassmorphism", True)
        
        # O WindowOpacity é o global da janela. Se usar Glass, 
        # a janela PRECISA estar 1.0 (opaca) pro Blur renderizar cantanhos
        
        # Fundo do Container
        bg_alpha = 10 if glass_enabled else 40
        self.central_widget.setStyleSheet(f"""
            #central_widget {{
                background-color: rgba(15, 15, 15, {bg_alpha});
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
            }}
        """)
        
        # Aplicar Blur
        apply_blur(self.winId(), enable=glass_enabled)

        # Input de Comandos (Oculto por padrão)
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Comando... (Esc para sair)")
        self.command_input.setStyleSheet("""
            QLineEdit { background: rgba(30, 30, 30, 40); color: white; border: 1px solid #555; padding: 5px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
        """)
        self.command_input.hide()
        self.command_input.returnPressed.connect(self.process_command)
        self.layout.addWidget(self.command_input)
        
        # Ativar Redimensionamento e Mouse Tracking
        self.setMouseTracking(True)
        self.central_widget.setMouseTracking(True)
        self.header.setMouseTracking(True)
        self.scroll_area.setMouseTracking(True)
        self.scroll_area.viewport().setMouseTracking(True)
        self.chat_container.setMouseTracking(True)
        
        self.RESIZE_MARGIN = 8
        self._resizing = False
        
        # Instalar Filtros de Evento para redimensionar mesmo sobre os filhos
        self.header.installEventFilter(self)
        self.scroll_area.installEventFilter(self)
        self.scroll_area.viewport().installEventFilter(self)
        self.chat_container.installEventFilter(self)
        
        self.add_message("Sistema", "🚀 Furious Multi Chat Pro Inicializado!", "system")
        
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

        flags = self.windowFlags()
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setToolTip("Janela TRAVADA (Não move) 📌")
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setToolTip("Janela DESTRAVADA")
        
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

    def _scroll_to_bottom(self):
        # Só rola se o usuário NÃO subiu o chat manualmente
        if self._auto_scroll and not self._user_scrolled:
            vbar = self.scroll_area.verticalScrollBar()
            vbar.setValue(vbar.maximum())

    def add_message(self, user, text, platform="twitch"):
        msg_widget = HeightAwareWidget()
        # FlowLayout permite quebra de linha individual per-widget
        msg_layout = FlowLayout(msg_widget, margin=6, spacing=4)
        msg_layout.setContentsMargins(6, 2, 6, 2)  # Margem top/bottom menor para compactar as mensagens
        msg_widget._animations = []  # Manter as animações vivas
        
        # Enviar para TTS Manager apenas mensagens de chat real (não eventos de follow/gift/share)
        if platform not in ("system", "tiktok_event") and hasattr(self, 'tts_manager'):
            self.tts_manager.add_message(user, text, platform)
            
        try:
            # Cores e Estilos dos Badges (Dinâmicos via Settings)
            platform_colors = {}
            font_family = "Segoe UI Variable Display"
            font_size = 11
            
            if hasattr(self, "settings_manager"):
                platform_colors = self.settings_manager.settings.get("platform_colors", {})
                font_family = self.settings_manager.settings.get("font_family", font_family)
                font_size = self.settings_manager.settings.get("font_size", font_size)
            
            # Fallbacks caso o dicionário esteja incompleto
            bg_color = platform_colors.get(platform, platform_colors.get("tiktok", "#555555") if platform == "tiktok_event" else "#555555")
            label_text = {"twitch": "TW", "tiktok": "TT", "tiktok_event": "TT", "kick": "KK", "system": "MSG"}.get(platform, "??")
            text_color = "black" if platform == "kick" else "white"
            
            icon_platform = "tiktok" if platform == "tiktok_event" else platform
            icon_path = resource_path(f"assets/{icon_platform.lower()}.png")
            badge_label = QLabel()
            badge_label.setFixedSize(22, 22)
            badge_label.setScaledContents(True)
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            icon_path = resource_path(f"assets/{platform.lower()}.png")
            pixmap = QPixmap(icon_path)
            
            if not pixmap.isNull():
                badge_label.setPixmap(pixmap)
                # APLICAR COR DE FUNDO NO BADGE MESMO COM ÍCONE (Para transparências mostraram a cor)
                badge_label.setStyleSheet(f"background-color: {bg_color}; border-radius: 4px; border: none;")
            else:
                # Fallback para texto (Sistema ou erro)
                badge_label.setText(label_text)
                badge_label.setFixedSize(30, 18)
                badge_label.setStyleSheet(f"""
                    background-color: {bg_color};
                    color: {text_color};
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 10px;
                    border: 1px solid rgba(255, 255, 255, 50);
                """)
            
            msg_layout.addWidget(badge_label)
            
            # USAR A COR DA PLATAFORMA TAMBÉM NO NOME DO USUÁRIO
            name_style = f"color: {bg_color};" if platform != "system" else "color: white;"
            qfont = QFont(font_family, font_size)
            qfont.setBold(True)
            
            def create_text(content):
                lbl = QLabel(content)
                lbl.setFont(qfont)
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setStyleSheet("color: white; background-color: transparent; margin: 0px; padding: 0px;")
                lbl.setContentsMargins(0, 0, 0, 0)
                return lbl

            # User (Pode vir com badges estáticos embutidos da própria classe handler)
            # Preserva as tags <img> dos badges mas escapa o texto do nome
            user_parts = re.split(r"(<img[^>]+>)", str(user))
            safe_user_parts = []
            for p in user_parts:
                if p.startswith("<img"):
                    safe_user_parts.append(p)
                else:
                    safe_user_parts.append(html.escape(p))
            safe_user = "".join(safe_user_parts)
            
            user_lbl = create_text(f"<span style='{name_style}'><b>{safe_user}:</b></span>")
            msg_layout.addWidget(user_lbl)
            
            # Parseando a mensagem para criar QLabel individual para palavras e QMovie para Emotes
            parts = re.split(r"(<img[^>]+>)", text)
            for part in parts:
                if not part: continue
                if part.startswith("<img"):
                    src_match = re.search(r"src=['\"]([^'\"]+)['\"]", part)
                    if src_match:
                        src = src_match.group(1)
                        
                        # Resolver caminhos internos (ex: 'gift.svg') para a pasta assets/ se não for URL ou caminho absoluto
                        if not src.startswith(("http", "file://", "data:")) and ":" not in src:
                            src = resource_path(f"assets/{src}")
                        
                        local_path = QUrl(src).toLocalFile() if src.startswith("file://") else src
                        
                        emote_lbl = QLabel()
                        emote_lbl.setScaledContents(True)
                        emote_lbl.setFixedSize(24, 24)
                        emote_lbl.setStyleSheet("background-color: transparent;")
                        
                        if src.startswith("data:image"):
                            # Suporte a ícones Base64 (presentes do TikTok)
                            try:
                                _, b64_data = src.split(",", 1)
                                from PyQt6.QtCore import QByteArray
                                img_data = QByteArray.fromBase64(b64_data.encode())
                                pixmap = QPixmap()
                                pixmap.loadFromData(img_data)
                                if not pixmap.isNull():
                                    emote_lbl.setPixmap(pixmap)
                            except Exception:
                                pass
                        elif local_path.endswith(".gif") or local_path.endswith(".webp"):

                            movie = QMovie(local_path)
                            movie.setScaledSize(QSize(24, 24))
                            emote_lbl.setMovie(movie)
                            movie.start()
                            msg_widget._animations.append(movie)
                        else:
                            emote_lbl.setPixmap(QPixmap(local_path))
                        
                        msg_layout.addWidget(emote_lbl)
                else:
                    # Textos são quebrados por palavras para o FlowLayout poder quebrar a linha na tela
                    words = part.split(' ')
                    for w in words:
                        if w:
                            safe_word = html.escape(str(w))
                            w_lbl = create_text(f"<b>{safe_word}</b>")
                            msg_layout.addWidget(w_lbl)
            
            # Adiciona a mensagem nativamente
            self.chat_layout.addWidget(msg_widget)
            
            # Força o limitador de largura para a nova mensagem quebrar a linha (WordWrap)
            vp_width = self.scroll_area.viewport().width()
            if vp_width > 0:
                self.chat_container.setFixedWidth(vp_width)
                # Calcular altura com um recuo (offset) de margem (25px para segurança com scrollbar e padding)
                # Isso impede que letras largas como 'D' forcem uma quebra de linha não prevista no cálculo original
                h = msg_layout.heightForWidth(vp_width - 25)
                if h > 0:
                    msg_widget.setMaximumHeight(h + 10)
            
            # Garante que o resize considere quebra de linha nova
            self.chat_layout.invalidate()
            
            # Limite de 200 mensagens
            if self.chat_layout.count() > 200:
                item = self.chat_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            
            # O ScrollArea resizable cuida da atualização de tamanho da tela automaticamente
            
            # Rola para o fundo automaticamente
            QTimer.singleShot(30, self._scroll_to_bottom)
            
            self.animate_message(msg_widget)
            
        except Exception as e:
            print(f"⚠️ Erro crítico ao renderizar mensagem de {user}: {e}")
            # Em caso de erro catastrófico na renderização rica, tenta adicionar o texto puro como fallback
            try:
                fallback_lbl = QLabel(f"[{user}]: {text}")
                fallback_lbl.setStyleSheet("color: white;")
                self.chat_layout.addWidget(fallback_lbl)
            except:
                pass

    def animate_message(self, widget):
        # Efeito de Opacidade
        opacity_effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)
        
        # Animação de Opacidade (Fade-in)
        fade_anim = QPropertyAnimation(opacity_effect, b"opacity", widget)
        fade_anim.setDuration(500)
        fade_anim.setStartValue(0)
        fade_anim.setEndValue(1)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        # Remover o efeito ao finalizar (Resolve bugs de transparência/ghosting)
        fade_anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        fade_anim.start()
        
        # Guardar referência para evitar GC prematuro
        widget._fade_anim = fade_anim
        widget.animations = [fade_anim]

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
                           not self.settings_btn.rect().contains(self.settings_btn.mapFromGlobal(global_pos)):
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
