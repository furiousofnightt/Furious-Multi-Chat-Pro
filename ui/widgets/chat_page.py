import re
import html
from PyQt6.QtCore import (
    Qt, QSize, QUrl, QByteArray, QTimer, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QFont, QPixmap, QMovie
from utils.resource_path import resource_path
from .notifications import JoinNotificationBanner
from .custom_layouts import FlowLayout, HeightAwareWidget


class ChatPageWidget(QWidget):
    """Página principal de chat (mensagens, banner de entrada e scroll responsivo)."""

    def __init__(self, parent=None, settings_manager=None, tts_manager=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.tts_manager = tts_manager
        self.current_text_opacity = 1.0
        self._auto_scroll = True   # Auto-scroll ativado por padrão
        self._user_scrolled = False # True = usuário subiu o chat manualmente

        self.setStyleSheet("background: transparent;")
        chat_page_layout = QVBoxLayout(self)
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

    def on_resize(self):
        # O Qt cuida do widget com setWidgetResizable(True) nativamente.
        # Porém, para forçar o WordWrap a funcionar (sem esticar pro infinito na horizontal):
        vp_width = self.scroll_area.viewport().width()
        if vp_width > 0:
            self.chat_container.setFixedWidth(vp_width)

        # Avisa ao layout interno para recalcular a altura
        if self.chat_layout:
            self.chat_layout.invalidate()

    def clear_chat(self):
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        if hasattr(self, 'join_banner'):
            self.join_banner.queue.clear()
            self.join_banner.fade_out()

    def add_user_joined(self, username, platform):
        """Encaminha o usuário que entrou para o banner de notificações"""
        if hasattr(self, 'join_banner'):
            self.join_banner.add_user(username, platform)

    def clear_platform_joins(self, platform):
        """Limpa a fila de notificações pendentes de uma plataforma desconectada."""
        if hasattr(self, 'join_banner'):
            self.join_banner.clear_platform(platform)

    def add_message(self, user, text, platform="twitch"):
        msg_widget = HeightAwareWidget()
        # FlowLayout permite quebra de linha individual per-widget
        msg_layout = FlowLayout(msg_widget, margin=6, spacing=4)
        msg_layout.setContentsMargins(6, 2, 6, 2)  # Margem top/bottom menor para compactar as mensagens
        msg_widget._animations = []  # Manter as animações vivas

        # Enviar para TTS Manager apenas mensagens de chat real (não eventos de follow/gift/share)
        tts = self.tts_manager or (self.parent().tts_manager if (self.parent() and hasattr(self.parent(), 'tts_manager')) else None)
        if platform not in ("system", "tiktok_event") and tts:
            tts.add_message(user, text, platform)

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
