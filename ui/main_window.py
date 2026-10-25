from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QSize, QUrl, QByteArray
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QScrollArea, QMenu, 
    QGraphicsOpacityEffect, QLineEdit, QHBoxLayout, QPushButton, 
    QSizePolicy, QApplication, QFrame, QSystemTrayIcon, QLayout, QLayoutItem, QWidgetItem,
    QStackedWidget
)
from PyQt6.QtGui import QColor, QPalette, QFont, QFontMetrics, QAction, QPixmap, QIcon, QMouseEvent, QMovie, QPainter, QPainterPath, QBrush, QPen
import re
import html
import os
import sys
import time
import base64
import threading
import httpx
from collections import deque
from utils.blur_window import apply_blur
from utils.translations import get_translation
from utils.resource_path import resource_path
from utils.tts_engine import TTSManager
from utils.avatar_utils import make_circular_pixmap_from_bytes, make_circular_image


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
        
class ViewerCardWidget(QFrame):
    """Card moderno de exibição de espectador com Rank, Avatar Circular, Nickname, Username e Score via SVGs."""
    _avatar_cache = {}
    _font_size = 15

    def __init__(self, viewer_info, parent=None):
        super().__init__(parent)
        self.viewer_info = viewer_info
        self.setFixedHeight(max(54, ViewerCardWidget._font_size * 3 + 12))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            ViewerCardWidget {
                background-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 9px;
            }
            ViewerCardWidget:hover {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(0, 230, 230, 90);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 12, 6)
        layout.setSpacing(10)

        # 1. Rank Badge / SVG
        rank = viewer_info.get('rank', 0)
        self.rank_lbl = QLabel()
        self.rank_lbl.setFixedSize(26, 26)
        self.rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rank_lbl.setStyleSheet("background: transparent; border: none;")

        if rank == 1:
            icon_path = resource_path("assets/rank_1.svg")
            if os.path.exists(icon_path):
                self.rank_lbl.setPixmap(QIcon(icon_path).pixmap(22, 22))
            else:
                self.rank_lbl.setText("1")
                self.rank_lbl.setStyleSheet("color: #FFD700; font-weight: 900; font-size: 14px; background: transparent; border: none;")
        elif rank == 2:
            icon_path = resource_path("assets/rank_2.svg")
            if os.path.exists(icon_path):
                self.rank_lbl.setPixmap(QIcon(icon_path).pixmap(22, 22))
            else:
                self.rank_lbl.setText("2")
                self.rank_lbl.setStyleSheet("color: #E0E0E0; font-weight: 900; font-size: 14px; background: transparent; border: none;")
        elif rank == 3:
            icon_path = resource_path("assets/rank_3.svg")
            if os.path.exists(icon_path):
                self.rank_lbl.setPixmap(QIcon(icon_path).pixmap(22, 22))
            else:
                self.rank_lbl.setText("3")
                self.rank_lbl.setStyleSheet("color: #CD7F32; font-weight: 900; font-size: 14px; background: transparent; border: none;")
        else:
            self.rank_lbl.setText(f"#{rank}")
            self.rank_lbl.setStyleSheet("color: #888888; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(self.rank_lbl)

        # 2. Avatar Circular com suporte a cache global
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(38, 38)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar_lbl)
        
        avatar_urls = viewer_info.get('avatar_urls', [])
        avatar_url = viewer_info.get('avatar_url', '')
        user_id = viewer_info.get('user_id', '')
        nickname = viewer_info.get('nickname', 'Usuário')
        self._load_avatar(avatar_url, avatar_urls, nickname, user_id)

        # 3. User Info (Nickname + @display_id)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.name_lbl = QLabel()
        self.name_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.name_lbl.setStyleSheet("background: transparent; border: none;")
        self.name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.name_lbl.setMinimumWidth(60)
        self._render_name()
        info_layout.addWidget(self.name_lbl)
        layout.addLayout(info_layout, stretch=1)

        # 4. Score / Points Badge Gamer com SVG Diamante
        score = viewer_info.get('score', 0)
        self.score_container = QWidget()
        score_layout = QHBoxLayout(self.score_container)
        score_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        if score > 0:
            self.score_container.setObjectName("score_pill_active")
            self.score_container.setStyleSheet("""
                QWidget#score_pill_active {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0, 230, 230, 0.28), stop:1 rgba(0, 160, 240, 0.16));
                    border: 1px solid rgba(0, 230, 230, 0.75);
                    border-radius: 13px;
                }
            """)
            score_layout.setContentsMargins(8, 4, 10, 4)
            score_layout.setSpacing(5)

            diamond_icon = QLabel()
            diamond_icon.setFixedSize(14, 14)
            diamond_icon.setScaledContents(True)
            dia_path = resource_path("assets/diamond.svg")
            if os.path.exists(dia_path):
                diamond_icon.setPixmap(QIcon(dia_path).pixmap(14, 14))
            diamond_icon.setStyleSheet("background: transparent; border: none;")
            score_layout.addWidget(diamond_icon)

            self.score_txt = QLabel(f"{score}")
            self.score_txt.setStyleSheet("color: #00ffff; font-size: 12px; font-weight: 900; font-family: Segoe UI, sans-serif; background: transparent; border: none;")
            score_layout.addWidget(self.score_txt)
        else:
            self.score_container.setObjectName("score_pill_zero")
            self.score_container.setStyleSheet("""
                QWidget#score_pill_zero {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }
            """)
            score_layout.setContentsMargins(8, 3, 8, 3)
            score_layout.setSpacing(0)

            dot_lbl = QLabel("0 pts")
            dot_lbl.setStyleSheet("color: #666666; font-size: 11px; font-weight: 600; background: transparent; border: none;")
            score_layout.addWidget(dot_lbl)

        layout.addWidget(self.score_container)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_w = event.size().width()
        if new_w > 100 and getattr(self, '_last_rendered_w', 0) != new_w:
            self._last_rendered_w = new_w
            self._render_name()

    def _render_name(self):
        """Renderiza o nome e @display_id com auto-ajuste de escala para caber perfeitamente na janela sem cortes."""
        nick = self.viewer_info.get('nickname', 'Usuário')
        disp = self.viewer_info.get('display_id', '')
        if disp and not disp.startswith('@'):
            disp = f"@{disp}"

        # Determina a largura disponível para o card
        w = self.width()
        if w < 150:
            win = self.window()
            if win and win.width() > 150:
                w = win.width() - 35
            else:
                w = 360

        # Subtrai margens, rank (26), avatar (38), score container (~65) e espaçamentos
        score_w = 65
        if hasattr(self, 'score_container') and self.score_container:
            sh = self.score_container.sizeHint().width()
            score_w = max(55, sh if sh > 0 else 65)

        avail_width = max(80, w - 116 - score_w)

        # Auto-escala suave da fonte do nickname até caber sem cortes
        nick_sz = ViewerCardWidget._font_size
        test_font = QFont(self.name_lbl.font())
        test_font.setBold(True)
        test_font.setPixelSize(nick_sz)
        metrics = QFontMetrics(test_font)
        while metrics.horizontalAdvance(nick) > avail_width and nick_sz > 8:
            nick_sz -= 1
            test_font.setPixelSize(nick_sz)
            metrics = QFontMetrics(test_font)

        # Auto-escala proporcional para o @display_id
        disp_sz = max(8, min(nick_sz - 1, ViewerCardWidget._font_size - 2))
        if disp:
            test_font.setBold(False)
            test_font.setPixelSize(disp_sz)
            disp_metrics = QFontMetrics(test_font)
            while disp_metrics.horizontalAdvance(disp) > avail_width and disp_sz > 7:
                disp_sz -= 1
                test_font.setPixelSize(disp_sz)
                disp_metrics = QFontMetrics(test_font)

        disp_html = f"<span style='color: #00e6e6; font-size: {disp_sz}px; font-weight: 600;'>{html.escape(disp)}</span>" if disp else ""
        self.name_lbl.setText(f"<span style='color: #ffffff; font-weight: bold; font-size: {nick_sz}px;'>{html.escape(nick)}</span><br>{disp_html}")

    def update_data(self, viewer_info):
        """Atualiza rank e score in-place sem recriar o widget."""
        self.viewer_info = viewer_info
        rank = viewer_info.get('rank', 0)
        if rank == 1:
            icon_path = resource_path("assets/rank_1.svg")
            if os.path.exists(icon_path):
                self.rank_lbl.setPixmap(QIcon(icon_path).pixmap(22, 22))
        elif rank == 2:
            icon_path = resource_path("assets/rank_2.svg")
            if os.path.exists(icon_path):
                self.rank_lbl.setPixmap(QIcon(icon_path).pixmap(22, 22))
        elif rank == 3:
            icon_path = resource_path("assets/rank_3.svg")
            if os.path.exists(icon_path):
                self.rank_lbl.setPixmap(QIcon(icon_path).pixmap(22, 22))
        else:
            self.rank_lbl.setText(f"#{rank}")
            self.rank_lbl.setStyleSheet("color: #888888; font-size: 12px; font-weight: bold; background: transparent; border: none;")

        score = viewer_info.get('score', 0)
        if hasattr(self, 'score_txt') and self.score_txt:
            self.score_txt.setText(f"{score}")

    def _load_avatar(self, avatar_url, avatar_urls, nickname, user_id):
        initial = (nickname[:1] or '?').upper()
        self.avatar_lbl.setText(initial)
        self.avatar_lbl.setStyleSheet("""
            QLabel {
                background-color: #1e232d;
                color: #00e6e6;
                border: 1px solid rgba(0, 230, 230, 160);
                border-radius: 19px;
                font-weight: bold;
                font-size: 14px;
            }
        """)

        # Coleta todas as URLs candidatas
        candidates = []
        if avatar_urls and isinstance(avatar_urls, list):
            candidates.extend([u for u in avatar_urls if u and u.startswith('http')])
        if avatar_url and avatar_url not in candidates:
            candidates.append(avatar_url)

        # Checa cache por user_id ou por URL
        cached_pix = None
        if user_id and user_id in ViewerCardWidget._avatar_cache:
            cached_pix = ViewerCardWidget._avatar_cache[user_id]
        if not cached_pix:
            for u in candidates:
                if u in ViewerCardWidget._avatar_cache:
                    cached_pix = ViewerCardWidget._avatar_cache[u]
                    break

        if cached_pix and not cached_pix.isNull():
            self.avatar_lbl.setText("")
            self.avatar_lbl.setPixmap(cached_pix)
            self.avatar_lbl.setStyleSheet("background: transparent; border: none;")
            return

        if not candidates:
            return

        def fetch_worker():
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/"
            }
            for candidate_url in candidates:
                try:
                    resp = httpx.get(candidate_url, headers=headers, timeout=6.0, follow_redirects=True)
                    if resp.status_code == 200 and resp.content:
                        circ_pix = make_circular_pixmap_from_bytes(resp.content, size=38, border_color="rgba(0, 230, 230, 180)", border_width=1.5)
                        if not circ_pix or circ_pix.isNull():
                            raw_pix = QPixmap()
                            if raw_pix.loadFromData(resp.content):
                                circ_pix = raw_pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                        
                        if circ_pix and not circ_pix.isNull():
                            if user_id:
                                ViewerCardWidget._avatar_cache[user_id] = circ_pix
                            ViewerCardWidget._avatar_cache[candidate_url] = circ_pix
                            
                            def update_ui(p=circ_pix):
                                if hasattr(self, 'avatar_lbl') and self.avatar_lbl:
                                    self.avatar_lbl.setText("")
                                    self.avatar_lbl.setPixmap(p)
                                    self.avatar_lbl.setStyleSheet("background: transparent; border: none;")
                            
                            QTimer.singleShot(0, update_ui)
                            break
                except Exception:
                    continue

        threading.Thread(target=fetch_worker, daemon=True).start()


class OnlineViewersListWidget(QWidget):
    """Página completa que lista os espectadores online do TikTok com header, botões e scroll."""
    back_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    sync_requested = pyqtSignal()

    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._last_signatures = None
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # Top Bar da página de viewers
        top_bar = QWidget()
        top_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 140);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 8px;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 5, 8, 5)
        top_layout.setSpacing(10)

        lang = self._get_lang()

        # Botão voltar para o chat
        self.back_btn = QPushButton(" " + get_translation("btn_back_to_chat", lang))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_back = QIcon(resource_path("assets/back_arrow.svg"))
        if not icon_back.isNull():
            self.back_btn.setIcon(icon_back)
            self.back_btn.setIconSize(QSize(14, 14))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 230, 230, 25);
                color: #00e6e6;
                border: 1px solid rgba(0, 230, 230, 80);
                border-radius: 5px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(0, 230, 230, 60);
                border: 1px solid rgba(0, 230, 230, 180);
                color: #ffffff;
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_layout.addWidget(self.back_btn)

        # Botões rápidos de controle de tamanho de fonte (A- e A+)
        font_box = QWidget()
        font_box.setStyleSheet("background: transparent; border: none;")
        fb_layout = QHBoxLayout(font_box)
        fb_layout.setContentsMargins(4, 0, 0, 0)
        fb_layout.setSpacing(3)

        self.font_dec_btn = QPushButton("A-")
        self.font_dec_btn.setToolTip(get_translation("tooltip_font_decrease", lang))
        self.font_dec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_dec_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 2px 7px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(0, 230, 230, 0.25);
                border: 1px solid rgba(0, 230, 230, 0.8);
                color: #ffffff;
            }
        """)
        self.font_dec_btn.clicked.connect(lambda: self.adjust_font_size(-1))
        fb_layout.addWidget(self.font_dec_btn)

        self.font_inc_btn = QPushButton("A+")
        self.font_inc_btn.setToolTip(get_translation("tooltip_font_increase", lang))
        self.font_inc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_inc_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 2px 7px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(0, 230, 230, 0.25);
                border: 1px solid rgba(0, 230, 230, 0.8);
                color: #ffffff;
            }
        """)
        self.font_inc_btn.clicked.connect(lambda: self.adjust_font_size(1))
        fb_layout.addWidget(self.font_inc_btn)

        top_layout.addWidget(font_box)

        # Botão de Sincronização Manual dos Espectadores
        self.sync_btn = QPushButton()
        self.sync_btn.setToolTip(get_translation("tooltip_sync_viewers", lang))
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setFixedSize(24, 24)
        icon_sync = QIcon(resource_path("assets/sync.svg"))
        if not icon_sync.isNull():
            self.sync_btn.setIcon(icon_sync)
            self.sync_btn.setIconSize(QSize(14, 14))
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 230, 230, 25);
                border: 1px solid rgba(0, 230, 230, 80);
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(0, 230, 230, 60);
                border: 1px solid rgba(0, 230, 230, 180);
            }
            QPushButton:pressed {
                background-color: rgba(0, 230, 230, 100);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 20);
            }
        """)
        self.sync_btn.clicked.connect(self.trigger_sync)
        top_layout.addWidget(self.sync_btn)

        top_layout.addStretch()

        # Ícone e Título / Contador
        self.users_icon_lbl = QLabel()
        self.users_icon_lbl.setFixedSize(16, 16)
        self.users_icon_lbl.setScaledContents(True)
        icon_users = QIcon(resource_path("assets/users.svg"))
        if not icon_users.isNull():
            self.users_icon_lbl.setPixmap(icon_users.pixmap(16, 16))
        self.users_icon_lbl.setStyleSheet("background: transparent; border: none;")
        top_layout.addWidget(self.users_icon_lbl)

        self.title_count_lbl = QLabel(get_translation("viewers_online_format", lang, count=0))
        self.title_count_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; background: transparent; border: none;")
        top_layout.addWidget(self.title_count_lbl)

        main_layout.addWidget(top_bar)

        # Scroll Area para a lista de viewers
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
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

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)

        # Placeholder padrão (vazio)
        self.empty_lbl = QLabel("Nenhum espectador na lista no momento.\nOs usuários aparecerão aqui durante a live.")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet(
            "color: #777777; font-size: 12px; padding: 40px 10px; "
            "background: transparent; border: none;"
        )
        self.list_layout.addWidget(self.empty_lbl)

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area)

        # Inicializa o estado correto da aba (placeholder ou banner se deslogado)
        self.refresh_state()

    def _get_settings_manager(self):
        if self._settings_manager:
            return self._settings_manager
        if self.parent() and hasattr(self.parent(), 'settings_manager'):
            return self.parent().settings_manager
        return None

    def _get_lang(self):
        sm = self._get_settings_manager()
        if sm and hasattr(sm, 'settings'):
            return sm.settings.get('language', 'pt-br')
        return 'pt-br'

    def _is_logged_in(self) -> bool:
        """Verifica se há um sessionid TikTok válido nas configurações."""
        sm = self._get_settings_manager()
        if sm and hasattr(sm, 'settings'):
            sid = sm.settings.get('tiktok_session_id', '')
            return bool(sid and str(sid).strip())
        return False

    def _has_tiktok_username(self) -> bool:
        """Verifica se há um canal TikTok configurado."""
        sm = self._get_settings_manager()
        if sm and hasattr(sm, 'settings'):
            user = sm.settings.get('tiktok', '')
            return bool(user and str(user).strip())
        return False

    def trigger_sync(self):
        """Dispara a sincronização manual e dá feedback visual imediato no próprio botão."""
        if not self._is_logged_in():
            print("[Espectadores] ⚠️ Login TikTok necessário para sincronizar.", flush=True)
            self.show_no_login_banner('no_login')
            return

        lang = self._get_lang()
        self.sync_btn.setEnabled(False)
        self.sync_btn.setToolTip(get_translation("btn_syncing", lang))
        self.sync_requested.emit()

        # Reabilita o botão após 2.5s para evitar flood na API
        QTimer.singleShot(2500, self._reset_sync_btn)

    def _reset_sync_btn(self):
        if hasattr(self, 'sync_btn') and self.sync_btn:
            lang = self._get_lang()
            self.sync_btn.setEnabled(True)
            self.sync_btn.setToolTip(get_translation("tooltip_sync_viewers", lang))

    def refresh_state(self):
        """Atualiza o estado visual da lista caso não haja cards de espectadores ativos."""
        # Se já existem cards de espectadores sendo exibidos, não mexe
        has_cards = any(
            isinstance(self.list_layout.itemAt(i).widget(), ViewerCardWidget)
            for i in range(self.list_layout.count())
            if self.list_layout.itemAt(i) and self.list_layout.itemAt(i).widget()
        )
        if has_cards:
            return

        if not self._is_logged_in():
            self.show_no_login_banner('no_login')
        else:
            self.show_empty_placeholder()

    def clear_viewers(self):
        """Limpa todos os espectadores da lista e reseta o contador."""
        if hasattr(self, 'title_count_lbl'):
            self.title_count_lbl.setText(get_translation("viewers_online_format", self._get_lang(), count=0))
        self.show_empty_placeholder()

    def show_empty_placeholder(self):
        """Exibe o placeholder padrão quando logado mas sem lista recebida ainda."""
        lang = self._get_lang()
        if hasattr(self, 'title_count_lbl'):
            self.title_count_lbl.setText(get_translation("viewers_online_format", lang, count=0))
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self.empty_lbl = QLabel(get_translation("viewers_empty", lang))
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet(
            "color: #777777; font-size: 12px; padding: 40px 10px; "
            "background: transparent; border: none;"
        )
        self.list_layout.addWidget(self.empty_lbl)
        self.list_layout.addStretch()

    def show_no_login_banner(self, mode: str = 'no_login'):
        """Substitui o conteúdo da lista por um banner visual.
        
        mode='no_login'    → avisa para fazer login TikTok nas Configurações
        mode='no_username' → avisa que o canal TikTok não está configurado
        """
        lang = self._get_lang()
        # Limpa lista atual e zera contagem
        if hasattr(self, 'title_count_lbl'):
            self.title_count_lbl.setText(get_translation("viewers_online_format", lang, count=0))
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Textos conforme modo
        if mode == 'no_username':
            title_text = get_translation("tiktok_not_configured_title", lang)
            desc_text = get_translation("tiktok_not_configured_desc", lang)
            hint_text = get_translation("tiktok_not_configured_hint", lang)
        else:  # no_login
            title_text = get_translation("tiktok_login_required_title", lang)
            desc_text = get_translation("tiktok_login_required_desc", lang)
            hint_text = get_translation("tiktok_login_required_hint", lang)

        # Card de aviso
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 69, 100, 0.12),
                    stop:1 rgba(255, 20, 60, 0.06));
                border: 1px solid rgba(255, 69, 100, 0.4);
                border-radius: 12px;
            }
        """)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(20, 24, 20, 24)
        banner_layout.setSpacing(14)
        banner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ícone TikTok
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        ttk_path = resource_path("assets/tiktok.png")
        if os.path.exists(ttk_path):
            icon_lbl.setPixmap(QIcon(ttk_path).pixmap(40, 40))
        else:
            icon_lbl.setText("🎵")
            icon_lbl.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        banner_layout.addWidget(icon_lbl)

        # Título
        title_lbl = QLabel(title_text)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            "color: #ff6b8a; font-size: 14px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        banner_layout.addWidget(title_lbl)

        # Descrição
        desc_lbl = QLabel(desc_text)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet(
            "color: #aaaaaa; font-size: 12px; line-height: 1.6; "
            "background: transparent; border: none;"
        )
        banner_layout.addWidget(desc_lbl)

        # Botão para abrir Configurações
        settings_btn = QPushButton(get_translation("btn_open_settings", lang))
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 69, 100, 0.7),
                    stop:1 rgba(200, 20, 80, 0.7));
                color: white;
                border: none;
                border-radius: 8px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 100, 130, 0.9),
                    stop:1 rgba(230, 50, 100, 0.9));
            }
            QPushButton:pressed {
                background: rgba(180, 20, 60, 0.9);
            }
        """)
        settings_btn.clicked.connect(self.open_settings_requested.emit)
        banner_layout.addWidget(settings_btn)

        # Dica extra
        hint_lbl = QLabel(hint_text)
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setStyleSheet(
            "color: #555555; font-size: 10px; font-style: italic; "
            "background: transparent; border: none;"
        )
        banner_layout.addWidget(hint_lbl)

        self.list_layout.addWidget(banner)
        self.list_layout.addStretch()

    def set_viewers(self, viewers_list):
        if not self._has_tiktok_username() or not viewers_list:
            self.clear_viewers()
            if hasattr(self, 'sync_btn') and not self.sync_btn.isEnabled():
                self._reset_sync_btn()
            return

        total_online = (viewers_list[0].get('total_online') if viewers_list else 0) or len(viewers_list)
        self.title_count_lbl.setText(get_translation("viewers_online_format", self._get_lang(), count=total_online))
        if hasattr(self, 'sync_btn') and not self.sync_btn.isEnabled():
            self._reset_sync_btn()

        # Checa se os widgets atuais já batem com a lista para atualizar in-place sem lag
        current_cards = []
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ViewerCardWidget):
                current_cards.append(item.widget())

        new_keys = [str(v.get('user_id') or v.get('display_id') or v.get('nickname')) for v in viewers_list]
        current_keys = [str(c.viewer_info.get('user_id') or c.viewer_info.get('display_id') or c.viewer_info.get('nickname')) for c in current_cards]

        if new_keys == current_keys and len(new_keys) > 0:
            # Mesma lista de pessoas: atualiza in-place instantaneamente
            for card, v_info in zip(current_cards, viewers_list):
                card.update_data(v_info)
            return

        # Lista mudou de ordem ou entraram novos usuários: reconstrói limpo
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for v in viewers_list:
            card = ViewerCardWidget(v, parent=self.list_container)
            self.list_layout.addWidget(card)

    def adjust_font_size(self, delta: int):
        """Aumenta ou diminui o tamanho da fonte dos nomes/@ e reconstrói os cards."""
        new_size = max(10, min(24, ViewerCardWidget._font_size + delta))
        if new_size == ViewerCardWidget._font_size:
            return
        ViewerCardWidget._font_size = new_size
        # Atualiza todos os cards existentes in-place
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ViewerCardWidget):
                card = item.widget()
                card._render_name()
                card.setFixedHeight(max(54, new_size * 3 + 12))


class LiveGiftCardWidget(QWidget):
    """Card moderno e compacto que exibe um presente recebido na live."""
    _avatar_cache = {}
    _font_size = 14

    def __init__(self, gift_info, parent=None):
        super().__init__(parent)
        self.gift_info = gift_info
        self.timestamp = gift_info.get('timestamp', time.time())
        self.setFixedHeight(70)
        self.setStyleSheet("""
            LiveGiftCardWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(28, 22, 20, 150),
                    stop:1 rgba(18, 18, 24, 150));
                border: 1px solid rgba(255, 180, 0, 45);
                border-radius: 8px;
            }
            LiveGiftCardWidget:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(42, 32, 24, 190),
                    stop:1 rgba(26, 26, 36, 190));
                border: 1px solid rgba(255, 200, 60, 130);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 10, 5)
        layout.setSpacing(8)

        # 1. Avatar Circular
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(36, 36)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar_lbl)

        # 2. Informações do Doador e Presente (Nome + @handle + Descrição)
        self.info_box = QWidget()
        self.info_box.setStyleSheet("background: transparent; border: none;")
        self.info_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.info_box.setMinimumWidth(50)
        info_layout = QVBoxLayout(self.info_box)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)

        self.name_lbl = QLabel()
        self.name_lbl.setStyleSheet("background: transparent; border: none;")
        self.name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.name_lbl.setMinimumWidth(40)

        self.handle_lbl = QLabel()
        self.handle_lbl.setStyleSheet("background: transparent; border: none;")
        self.handle_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.handle_lbl.setMinimumWidth(40)

        self.desc_lbl = QLabel()
        self.desc_lbl.setStyleSheet("background: transparent; border: none;")
        self.desc_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.desc_lbl.setMinimumWidth(40)

        info_layout.addWidget(self.name_lbl)
        info_layout.addWidget(self.handle_lbl)
        info_layout.addWidget(self.desc_lbl)
        layout.addWidget(self.info_box, 1)

        # 3. Box da direita: Ícone do presente + badge x10 + tempo relativo
        self.gift_box = QWidget()
        self.gift_box.setStyleSheet("background: transparent; border: none;")
        self.gift_box.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        gift_layout = QVBoxLayout(self.gift_box)
        gift_layout.setContentsMargins(0, 0, 0, 0)
        gift_layout.setSpacing(2)
        gift_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top_right = QWidget()
        top_right.setStyleSheet("background: transparent; border: none;")
        tr_layout = QHBoxLayout(top_right)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        tr_layout.setSpacing(4)
        tr_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        self.icon_lbl.setScaledContents(True)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        tr_layout.addWidget(self.icon_lbl)

        count = gift_info.get('gift_count', 1)
        self.count_badge = QLabel(f"x{count}")
        self.count_badge.setFont(QFont("Segoe UI Black", 10, QFont.Weight.Black))
        self.count_badge.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI Black', 'Arial Black', Impact, sans-serif;
                font-weight: 900;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 110, 0, 230),
                    stop:1 rgba(255, 170, 0, 240));
                color: #ffffff;
                font-size: 11px;
                border-radius: 4px;
                padding: 1px 6px;
                border: 1px solid rgba(255, 230, 120, 220);
            }
        """)
        tr_layout.addWidget(self.count_badge)
        gift_layout.addWidget(top_right)

        self.time_lbl = QLabel()
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.time_lbl.setStyleSheet("color: #888888; font-size: 10px; font-weight: 500; background: transparent; border: none;")
        gift_layout.addWidget(self.time_lbl)

        layout.addWidget(self.gift_box, 0)

        self._render_data()
        self._load_avatar()
        self._load_gift_icon()
        self.update_relative_time()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_w = event.size().width()
        if new_w > 100 and getattr(self, '_last_rendered_w', 0) != new_w:
            self._last_rendered_w = new_w
            self._render_data()

    def _render_data(self):
        user = self.gift_info.get('user', 'Usuário')
        disp = self.gift_info.get('display_id', '')
        gift_name = self.gift_info.get('gift_name', 'Presente')
        diamond_count = self.gift_info.get('diamond_count', 0)
        gift_count = self.gift_info.get('gift_count', 1)
        total_diamonds = diamond_count * gift_count if diamond_count > 0 else 0

        # Determina a largura disponível para a área de texto de forma responsiva
        w = self.width()
        if w < 150:
            win = self.window()
            if win and win.width() > 150:
                w = win.width() - 35
            else:
                w = 360

        gift_box_w = 75
        if hasattr(self, 'gift_box') and self.gift_box:
            sh = self.gift_box.sizeHint().width()
            gift_box_w = max(60, sh if sh > 0 else 75)

        avail_width = max(60, w - 70 - gift_box_w)

        # Badges do usuário (Moderador, Fã-Clube, Nível de Doador, etc.)
        prefix_badges = self.gift_info.get('prefix_badges', '')
        suffix_badges = self.gift_info.get('suffix_badges', '')

        # Fallback: extrai do author_display caso não tenham sido passados separadamente
        if not prefix_badges and not suffix_badges:
            author_display = self.gift_info.get('author_display', '')
            if author_display:
                ad = str(author_display)
                avatar_html = str(self.gift_info.get('avatar_html', '') or '')
                if avatar_html and avatar_html in ad:
                    ad = ad.replace(avatar_html, '')
                if '<img' in ad:
                    if user in ad:
                        parts = ad.split(user, 1)
                        prefix_badges = parts[0]
                        suffix_badges = parts[1]
                    else:
                        prefix_badges = ad

        # Se houver badges antes/depois do nome, garante espaçamento limpo
        p_badge_html = f"{prefix_badges} " if (prefix_badges and not prefix_badges.endswith(' ')) else (prefix_badges or '')
        s_badge_html = f" {suffix_badges}" if (suffix_badges and not suffix_badges.startswith(' ')) else (suffix_badges or '')

        # Auto-escala suave da fonte do usuário até caber sem estourar o card
        nick_sz = LiveGiftCardWidget._font_size
        test_font = QFont(self.name_lbl.font())
        test_font.setBold(True)
        test_font.setPixelSize(nick_sz)
        metrics = QFontMetrics(test_font)
        while metrics.horizontalAdvance(user) > avail_width and nick_sz > 8:
            nick_sz -= 1
            test_font.setPixelSize(nick_sz)
            metrics = QFontMetrics(test_font)

        if metrics.horizontalAdvance(user) > avail_width:
            user_display = metrics.elidedText(user, Qt.TextElideMode.ElideRight, avail_width)
        else:
            user_display = user

        nick_html = f"{p_badge_html}<span style='color: #ffffff; font-weight: bold; font-size: {nick_sz}px;'>{html.escape(user_display)}</span>{s_badge_html}"
        self.name_lbl.setText(nick_html)

        # @handle sempre na linha de baixo do nome com auto-escala e elide responsivo
        if not disp:
            disp = user
        if not disp.startswith('@'):
            disp = f"@{disp}"

        disp_sz = max(8, min(nick_sz - 1, 11))
        test_font.setBold(False)
        test_font.setPixelSize(disp_sz)
        disp_metrics = QFontMetrics(test_font)
        while disp_metrics.horizontalAdvance(disp) > avail_width and disp_sz > 7:
            disp_sz -= 1
            test_font.setPixelSize(disp_sz)
            disp_metrics = QFontMetrics(test_font)

        if disp_metrics.horizontalAdvance(disp) > avail_width:
            disp_display = disp_metrics.elidedText(disp, Qt.TextElideMode.ElideRight, avail_width)
        else:
            disp_display = disp

        self.handle_lbl.setText(f"<span style='color: #ffffff; font-size: {disp_sz}px;'>{html.escape(disp_display)}</span>")

        desc_parts = [f"<span style='color: #ffb400; font-size: 13px;'>enviou <b>{html.escape(gift_name)}</b></span>"]
        if total_diamonds > 0:
            desc_parts.append(f"<span style='color: #00e6e6; font-size: 13px; font-weight: 900; font-family: \"Segoe UI Black\", \"Arial Black\", Impact, sans-serif;'>💎 {total_diamonds}</span>")

        self.desc_lbl.setText(" ".join(desc_parts))

    def _load_avatar(self):
        avatar_html = self.gift_info.get('avatar_html', '')
        user_id = self.gift_info.get('display_id') or self.gift_info.get('user')

        if user_id and user_id in LiveGiftCardWidget._avatar_cache:
            pix = LiveGiftCardWidget._avatar_cache[user_id]
            if pix and not pix.isNull():
                self.avatar_lbl.setPixmap(pix)
                self.avatar_lbl.setStyleSheet("background: transparent; border: none;")
                return

        if avatar_html and "data:image" in avatar_html:
            try:
                m = re.search(r"src=['\"]data:image/[^;]+;base64,([^'\"]+)['\"]", avatar_html)
                if m:
                    b64 = m.group(1)
                    raw_bytes = base64.b64decode(b64)
                    circ_pix = make_circular_pixmap_from_bytes(raw_bytes, size=36, border_color="rgba(255, 180, 0, 180)", border_width=1.5)
                    if circ_pix and not circ_pix.isNull():
                        if user_id:
                            LiveGiftCardWidget._avatar_cache[user_id] = circ_pix
                        self.avatar_lbl.setPixmap(circ_pix)
                        self.avatar_lbl.setStyleSheet("background: transparent; border: none;")
                        return
            except Exception:
                pass

        initial = (self.gift_info.get('user', '?')[:1] or '?').upper()
        self.avatar_lbl.setText(initial)
        self.avatar_lbl.setStyleSheet("""
            QLabel {
                background-color: #2a2015;
                color: #ffb400;
                border: 1.5px solid rgba(255, 180, 0, 160);
                border-radius: 18px;
                font-weight: bold;
                font-size: 13px;
            }
        """)

    def _load_gift_icon(self):
        icon_html = self.gift_info.get('icon_html', '')
        if icon_html and "data:image" in icon_html:
            try:
                m = re.search(r"src=['\"]data:image/[^;]+;base64,([^'\"]+)['\"]", icon_html)
                if m:
                    b64 = m.group(1)
                    qba = QByteArray.fromBase64(b64.encode())
                    pix = QPixmap()
                    if pix.loadFromData(qba):
                        self.icon_lbl.setPixmap(pix.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        return
            except Exception:
                pass

        fallback_path = resource_path("assets/gift_tab.svg")
        if os.path.exists(fallback_path):
            self.icon_lbl.setPixmap(QIcon(fallback_path).pixmap(22, 22))

    def update_relative_time(self, lang="pt-br"):
        diff = max(0, int(time.time() - self.timestamp))
        if diff < 60:
            text = get_translation("gift_time_now", lang)
        elif diff < 3600:
            m = diff // 60
            text = get_translation("gift_time_min", lang, m=m)
        elif diff < 86400:
            h = diff // 3600
            text = get_translation("gift_time_hour", lang, h=h)
        else:
            d = diff // 86400
            text = get_translation("gift_time_day", lang, d=d)
        self.time_lbl.setText(text)


class LiveGiftsListWidget(QWidget):
    """Página completa que lista os presentes recebidos na live com header, botões e scroll."""
    back_requested = pyqtSignal()

    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self.setStyleSheet("background: transparent;")
        self._total_gifts_count = 0
        self._cards = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # Top Bar da página de presentes
        top_bar = QWidget()
        top_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 140);
                border: 1px solid rgba(255, 180, 0, 30);
                border-radius: 8px;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 5, 8, 5)
        top_layout.setSpacing(8)

        lang = self._get_lang()

        # Botão voltar para o chat
        self.back_btn = QPushButton(" " + get_translation("btn_back_to_chat", lang))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_back = QIcon(resource_path("assets/back_arrow.svg"))
        if not icon_back.isNull():
            self.back_btn.setIcon(icon_back)
            self.back_btn.setIconSize(QSize(14, 14))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 180, 0, 25);
                color: #ffb400;
                border: 1px solid rgba(255, 180, 0, 80);
                border-radius: 5px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 180, 0, 60);
                border: 1px solid rgba(255, 200, 50, 180);
                color: #ffffff;
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_layout.addWidget(self.back_btn)

        # Botão Limpar Presentes
        self.clear_btn = QPushButton(" " + get_translation("btn_clear_gifts", lang))
        self.clear_btn.setToolTip(get_translation("tooltip_clear_gifts", lang))
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_clear = QIcon(resource_path("assets/clear.svg"))
        if not icon_clear.isNull():
            self.clear_btn.setIcon(icon_clear)
            self.clear_btn.setIconSize(QSize(12, 12))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 69, 100, 0.25);
                border: 1px solid rgba(255, 69, 100, 0.8);
                color: #ffffff;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_gifts)
        top_layout.addWidget(self.clear_btn)

        top_layout.addStretch()

        # Ícone de Presente e Contador
        self.gift_icon_lbl = QLabel()
        self.gift_icon_lbl.setFixedSize(18, 18)
        self.gift_icon_lbl.setScaledContents(True)
        icon_gift = QIcon(resource_path("assets/gift_tab.svg"))
        if not icon_gift.isNull():
            self.gift_icon_lbl.setPixmap(icon_gift.pixmap(18, 18))
        self.gift_icon_lbl.setStyleSheet("background: transparent; border: none;")
        top_layout.addWidget(self.gift_icon_lbl)

        self.title_count_lbl = QLabel(get_translation("gifts_count_format", lang, count=0))
        self.title_count_lbl.setStyleSheet("color: #ffb400; font-weight: bold; font-size: 12px; background: transparent; border: none;")
        top_layout.addWidget(self.title_count_lbl)

        main_layout.addWidget(top_bar)

        # Scroll Area para os presentes
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
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
                background: rgba(255, 180, 0, 100);
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area)

        # Timer para atualizar os tempos relativos (a cada 30 segundos)
        self.time_update_timer = QTimer(self)
        self.time_update_timer.timeout.connect(self._refresh_relative_times)
        self.time_update_timer.start(30000)

        # Placeholder inicial (vazio)
        self.show_empty_placeholder()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for card in self._cards:
            if hasattr(card, '_render_data'):
                card._render_data()

    def _get_settings_manager(self):
        if self._settings_manager:
            return self._settings_manager
        if self.parent() and hasattr(self.parent(), 'settings_manager'):
            return self.parent().settings_manager
        return None

    def _get_lang(self):
        sm = self._get_settings_manager()
        if sm and hasattr(sm, 'settings'):
            return sm.settings.get('language', 'pt-br')
        return 'pt-br'

    def _refresh_relative_times(self):
        lang = self._get_lang()
        for card in self._cards:
            card.update_relative_time(lang)

    def show_empty_placeholder(self):
        lang = self._get_lang()
        self.title_count_lbl.setText(get_translation("gifts_count_format", lang, count=self._total_gifts_count))
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        empty_container = QWidget()
        empty_container.setStyleSheet("background: transparent; border: none;")
        el = QVBoxLayout(empty_container)
        el.setContentsMargins(20, 40, 20, 20)
        el.setSpacing(12)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_img = QLabel()
        empty_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_img.setStyleSheet("background: transparent; border: none;")
        empty_pix = QIcon(resource_path("assets/gift_empty.svg")).pixmap(64, 64)
        if not empty_pix.isNull():
            empty_img.setPixmap(empty_pix)
        el.addWidget(empty_img)

        empty_text = QLabel(get_translation("gifts_empty", lang))
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet("color: #777777; font-size: 12px; line-height: 1.5; background: transparent; border: none;")
        el.addWidget(empty_text)

        self.list_layout.addWidget(empty_container)
        self.list_layout.addStretch()

    def add_gift(self, gift_data):
        print(f"[Presentes] 📋 LiveGiftsListWidget.add_gift: {gift_data.get('gift_name')} de {gift_data.get('user')}", flush=True)
        if not self._cards:
            while self.list_layout.count() > 0:
                item = self.list_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()

        card = LiveGiftCardWidget(gift_data, parent=self.list_container)
        self.list_layout.addWidget(card)
        self._cards.append(card)

        # Propagar eventFilter e mouseTracking do ChatWindow para o card e seus filhos
        chat_window = self.window()
        if chat_window and chat_window is not self:
            card.setMouseTracking(True)
            card.installEventFilter(chat_window)
            for child in card.findChildren(QWidget):
                child.setMouseTracking(True)
                child.installEventFilter(chat_window)

        self._total_gifts_count += gift_data.get('gift_count', 1)
        lang = self._get_lang()
        self.title_count_lbl.setText(get_translation("gifts_count_format", lang, count=self._total_gifts_count))

        if len(self._cards) > 200:
            old_card = self._cards.pop(0)
            self.list_layout.removeWidget(old_card)
            old_card.deleteLater()

        # Rola automaticamente para o último presente (mais novo embaixo)
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def clear_gifts(self):
        self._total_gifts_count = 0
        self._cards.clear()
        self.show_empty_placeholder()




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
        if hasattr(self, 'join_banner'):
            self.join_banner.add_user(username, platform)

    def clear_platform_joins(self, platform):
        """Limpa a fila de notificações pendentes de uma plataforma desconectada."""
        if hasattr(self, 'join_banner'):
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

        # --- PÁGINA 0: CHAT GERAL ---
        self.chat_page = QWidget()
        self.chat_page.setStyleSheet("background: transparent;")
        chat_page_layout = QVBoxLayout(self.chat_page)
        chat_page_layout.setContentsMargins(0, 0, 0, 0)
        chat_page_layout.setSpacing(0)

        # Banner de Notificação de Entrada (Fixo para não quebrar o Scroll)
        self.notification_container = QWidget()
        self.notification_container.setFixedHeight(45) # Altura fixa reservada
        notification_layout = QHBoxLayout(self.notification_container)
        notification_layout.setContentsMargins(0, 5, 0, 5)
        notification_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.join_banner = JoinNotificationBanner(self)
        notification_layout.addWidget(self.join_banner)
        chat_page_layout.addWidget(self.notification_container)
        
        # Área de Scroll para as mensagens
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        self.scroll_area.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
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
        self.chat_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setContentsMargins(10, 5, 25, 5)
        self.chat_layout.setSpacing(15)
        
        self.scroll_area.setWidget(self.chat_container)
        
        vbar = self.scroll_area.verticalScrollBar()
        vbar.valueChanged.connect(self.handle_scroll_value_changed)
        vbar.rangeChanged.connect(self.handle_scroll_range_changed)
        
        chat_page_layout.addWidget(self.scroll_area)
        self.stacked_widget.addWidget(self.chat_page)

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

    def apply_theme(self, settings_dict):
        """ Aplica configurações visuais: Opacidade do Fundo, Opacidade de Texto e Blur do Windows """
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

        # Fundo do Container (#central_widget) com transparência escura real (FUMÊ PRETO)
        bg_alpha = int(bg_opacity * 255)
        self.central_widget.setStyleSheet(f"""
            #central_widget {{
                background-color: rgba(0, 0, 0, {bg_alpha});
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 10px;
            }}
        """)

        # Garantir que a chat_page e stacked_widget sejam 100% transparentes sem nenhum efeito cinza
        if hasattr(self, 'chat_page'):
            self.chat_page.setGraphicsEffect(None)
            self.chat_page.setStyleSheet("background: transparent;")
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setStyleSheet("background: transparent;")

        # Aplicar opacidade de texto do chat de forma limpa via CSS (sem QGraphicsOpacityEffect)
        text_alpha = int(text_opacity * 255)
        self.current_text_opacity = text_opacity
        if hasattr(self, 'chat_container'):
            self.chat_container.setStyleSheet(f"background: transparent; QLabel {{ color: rgba(255, 255, 255, {text_alpha}); }}")

        # Aplicar Blur / Mica / BlurBehind nativo
        # Passa a cor de gradiente escuro com canal alfa correspondente
        hex_alpha = f"{min(255, max(10, bg_alpha)):02X}"
        apply_blur(self.winId(), enable=glass_enabled, hex_color=f"#000000{hex_alpha}")

        # Input de Comandos (Oculto por padrão, criado uma única vez)
        lang = self.settings_manager.settings.get("language", "pt-br") if hasattr(self, "settings_manager") else "pt-br"
        if not hasattr(self, 'command_input'):
            self.command_input = QLineEdit()
            self.command_input.setPlaceholderText(get_translation("placeholder_command", lang))
            self.command_input.setStyleSheet("""
                QLineEdit { background: rgba(30, 30, 30, 180); color: white; border: 1px solid #555; padding: 5px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
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
            label_text = {"twitch": "TW", "tiktok": "TT", "tiktok_event": "TT", "kick": "KK", "youtube": "YT", "system": "MSG"}.get(platform, "??")
            text_color = "black" if platform == "kick" else "white"
            
            icon_platform = "tiktok" if platform == "tiktok_event" else platform
            icon_path = resource_path(f"assets/{icon_platform.lower()}.png")
            badge_label = QLabel()
            badge_label.setFixedSize(22, 22)
            badge_label.setScaledContents(True)
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
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
            
            text_alpha = int(getattr(self, 'current_text_opacity', 1.0) * 255)
            def create_text(content):
                lbl = QLabel(content)
                lbl.setFont(qfont)
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setStyleSheet(f"color: rgba(255, 255, 255, {text_alpha}); background-color: transparent; margin: 0px; padding: 0px;")
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
                    # Textos são quebrados por palavras para o FlowLayout poder quebrar a linha na tela.
                    # PROBLEMA CJK: Japonês/Chinês/Coreano não usa espaços, então um texto longo como
                    # "家族の応援に感謝します" vira uma única "palavra" de 400px que não cabe e não quebra.
                    # SOLUÇÃO: Detectar caracteres CJK e chunkar em grupos de 6 para permitir wrapping.
                    def _has_cjk(s):
                        for c in s:
                            cp = ord(c)
                            if (0x4E00 <= cp <= 0x9FFF or  # CJK Unificado (Chinês/Japonês/Coreano)
                                0x3040 <= cp <= 0x309F or  # Hiragana
                                0x30A0 <= cp <= 0x30FF or  # Katakana
                                0xFF00 <= cp <= 0xFFEF or  # Forma de largura total
                                0x3000 <= cp <= 0x303F):   # Símbolos e Pontuação CJK
                                return True
                        return False

                    words = part.split(' ')
                    for w in words:
                        if not w:
                            continue
                        # Se a "palavra" contiver CJK e for longa, quebrar em chunks de 6 chars
                        # 6 chars CJK ≈ 90px de largura, cabe bem numa janela de 405px
                        if _has_cjk(w) and len(w) > 6:
                            chunks = [w[i:i+6] for i in range(0, len(w), 6)]
                        else:
                            chunks = [w]
                        for chunk in chunks:
                            safe_word = html.escape(str(chunk))
                            w_lbl = create_text(f"<b>{safe_word}</b>")
                            msg_layout.addWidget(w_lbl)
            
            # Adiciona a mensagem nativamente
            self.chat_layout.addWidget(msg_widget)
            
            # Força o limitador de largura para a nova mensagem quebrar a linha (WordWrap)
            vp_width = self.scroll_area.viewport().width()
            if vp_width > 0:
                self.chat_container.setFixedWidth(vp_width)
                # Margem total real:
                #   chat_layout: 10px (esq) + 25px (dir) = 35px
                #   msg_layout:   6px (esq) +  6px (dir) = 12px
                #   Total: ~47px + 5px de segurança extra = 52px
                # Usar offset correto evita subestimar o número de linhas
                # e o +20 de buffer vertical garante que nenhuma linha seja cortada
                h = msg_layout.heightForWidth(vp_width - 52)
                if h > 0:
                    msg_widget.setMaximumHeight(h + 20)
            
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
