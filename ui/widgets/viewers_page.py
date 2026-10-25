import os
import html
import threading
import httpx
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont, QFontMetrics, QPixmap
from utils.resource_path import resource_path
from utils.translations import get_translation
from utils.avatar_utils import make_circular_pixmap_from_bytes


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
