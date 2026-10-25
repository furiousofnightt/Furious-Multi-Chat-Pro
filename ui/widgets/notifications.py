from collections import deque
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QGraphicsOpacityEffect, QWidget
from PyQt6.QtGui import QIcon, QFont, QFontMetrics
from utils.resource_path import resource_path
from utils.translations import get_translation


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

    def clear_platform(self, platform):
        """Remove todos os usuários pendentes dessa plataforma da fila."""
        self.queue = deque([item for item in self.queue if item[1] != platform])
        # Se a notificação atual for dessa plataforma e estiver visível, podemos deixá-la terminar (leva max 3s)
        # ou ocultá-layer imediatamente, mas a fila pendente já foi apagada.

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


