import time
import re
import base64
import os
import html
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QByteArray
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont, QFontMetrics, QPixmap
from utils.resource_path import resource_path
from utils.translations import get_translation
from utils.avatar_utils import make_circular_pixmap_from_bytes


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
