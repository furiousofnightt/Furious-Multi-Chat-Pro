from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QSlider, QComboBox, QCheckBox, QPlainTextEdit, QWidget, QFrame, QScrollArea, QMessageBox, QColorDialog
from PyQt6.QtGui import QColor, QIcon, QFont, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QObject
from utils.translations import get_translation, get_available_languages, get_language_display_name
from utils.resource_path import resource_path
from ui.main_window import FlowLayout, HeightAwareWidget
import os

# Helper para recursos

class _WheelIgnoreFilter(QObject):
    """Ignora eventos de scroll do mouse em widgets dentro de QScrollArea.
    Sem isso, QSlider e QComboBox dentro de um scroll roubam o scroll do painel.
    """
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            event.ignore()  # devolve o evento para o pai (o scroll area)
            return True
        return super().eventFilter(obj, event)

# Instância global reutilizável (evita criar um objeto por widget)
_wheel_ignore = _WheelIgnoreFilter()

class HotkeyField(QLineEdit):
    """Campo que captura o atalho de teclado quando o usuário pressiona as teclas."""
    def __init__(self, placeholder=None, parent=None, lang="pt-br"):
        super().__init__(parent)
        self.lang = lang
        ph = placeholder if placeholder else get_translation("hotkey_press_keys", self.lang)
        self.setPlaceholderText(ph)
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._capturing = False
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a; color: white;
                border: 1px solid #555; padding: 5px; border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
                background-color: #1e3a4a;
            }
        """)
    
    def mousePressEvent(self, event):
        self._capturing = True
        self.setText("")
        self.setPlaceholderText(get_translation("hotkey_capturing", self.lang))
        self.setFocus()
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        if not self._capturing:
            return
        
        key = event.key()
        # Ignora teclas modificadoras sozinhas
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
        
        # Escape cancela a captura
        if key == Qt.Key.Key_Escape:
            self._capturing = False
            self.setPlaceholderText(get_translation("hotkey_press_keys", self.lang))
            return
        
        parts = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:   parts.append("shift")
        if mods & Qt.KeyboardModifier.AltModifier:     parts.append("alt")
        
        # Converte o nome da tecla para minúsculas simples
        key_text = QKeySequence(key).toString().lower()
        if key_text:
            parts.append(key_text)
        
        combo = "+".join(parts)
        self.setText(combo)
        self._capturing = False
        self.setPlaceholderText(get_translation("hotkey_press_keys", self.lang))
        self.clearFocus()


class TagWidget(QWidget):
    removed = pyqtSignal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(5)
        
        label = QLabel(text)
        label.setStyleSheet("color: white; font-weight: bold; border: none; background: transparent;")
        
        del_btn = QPushButton()
        del_btn.setFixedSize(18, 18)
        del_btn.setIcon(QIcon(resource_path("assets/exit.svg"))) # Usar o ícone de saída (porta) ou criar um X
        del_btn.setIconSize(self.parent().iconSize() if hasattr(self.parent(), 'iconSize') else (QSize(10, 10))) 
        # Na verdade, melhor usar um CSS para o X ou um SVG de fechar dedicado.
        # Vou usar o exit.svg por enquanto mas bem pequeno.
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton { 
                background: #666; 
                border-radius: 9px; 
            }
            QPushButton:hover { background-color: #ff4444; }
        """)
        del_btn.clicked.connect(lambda: self.removed.emit(self.text))
        
        layout.addWidget(label)
        layout.addWidget(del_btn)
        
        # Estilo do balão
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            TagWidget {
                background-color: #4a4a4a;
                border-radius: 10px;
                border: 1px solid #666;
            }
            TagWidget:hover { background-color: #555; border: 1px solid #888; }
        """)

class ConfigWindow(QDialog):
    def __init__(self, settings_manager, main_window, chat_manager=None):
        super().__init__(main_window)
        
        # Seta o ícone para a janelinha de config
        icon_path = resource_path("assets/icone.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings_manager = settings_manager
        self.main_window = main_window
        self.chat_manager = chat_manager
        self.tags = []
        self.init_ui()
        
        if self.chat_manager:
            self.chat_manager.status_changed.connect(self.update_platform_status)

    def init_ui(self):
        lang = self.settings_manager.settings.get("language", "pt-br")
        
        self.setWindowTitle("Furious Config")
        self.setMinimumWidth(900)
        self.setMinimumHeight(680)
        self.resize(900, 700)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        self.status_labels = {}
        
        # Estilização global
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; color: white; }
            QLabel { color: #ccc; font-weight: bold; margin-top: 6px; font-size: 11px; }
            QLabel.section-title { color: #ffffff; font-size: 12px; margin-bottom: 2px; }
            QLineEdit, QPlainTextEdit, QComboBox {
                background-color: #2e2e2e; color: white;
                border: 1px solid #4a4a4a; padding: 5px 8px; border-radius: 5px;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #007acc; }
            QComboBox QAbstractItemView { background-color: #2e2e2e; color: white; selection-background-color: #007acc; }
            QPushButton { background-color: #3a3a3a; color: white; border: none; padding: 7px 12px; border-radius: 5px; font-size: 11px; }
            QPushButton:hover { background-color: #505050; }
            QPushButton#save_btn { background-color: #007acc; font-weight: bold; font-size: 13px; padding: 10px; }
            QPushButton#save_btn:hover { background-color: #0090e0; }
            QPushButton#quit_btn { background-color: transparent; color: #ff6666; font-size: 11px; border: 1px solid #ff6666; }
            QPushButton#quit_btn:hover { background-color: #ff6666; color: white; }
            QCheckBox { color: #ccc; margin-top: 4px; font-size: 11px; }
            QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }
            QSlider::handle:horizontal { background: #007acc; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #007acc; border-radius: 2px; }
            QFrame#panel {
                background-color: #242424;
                border: 1px solid #333;
                border-radius: 8px;
            }
            QScrollArea { border: none; background: transparent; }
        """)

        # ── DOIS PAINÉIS LADO A LADO ──────────────────────────────────────────
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(12)

        # ── PAINEL ESQUERDO: Conexões + Geral (com scroll para acomodar conteúdo) ─
        # Conteúdo interno do painel esquerdo
        left_content = QWidget()
        left_content.setObjectName("left_content")
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(5)

        def section_label(text, layout, icon_filename=None):
            container = QFrame()
            h_lay = QHBoxLayout(container)
            h_lay.setContentsMargins(0, 2, 0, 4)
            h_lay.setSpacing(6)
            
            if icon_filename:
                icon_path = resource_path(f"assets/{icon_filename}")
                icon_lbl = QLabel()
                pixmap = QIcon(icon_path).pixmap(16, 16)
                icon_lbl.setPixmap(pixmap)
                h_lay.addWidget(icon_lbl)
                
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #007acc; font-size: 13px; font-weight: bold;")
            h_lay.addWidget(lbl)
            h_lay.addStretch()
            layout.addWidget(container)

        section_label(get_translation("connections_section", lang), left_layout, "icon_link.svg")
        self._add_config_field_to("twitch", get_translation("twitch_label", lang), left_layout)
        self._add_config_field_to("tiktok", get_translation("tiktok_label", lang), left_layout)
        self._add_config_field_to("kick",   get_translation("kick_label", lang),   left_layout)
        self._add_config_field_to("youtube", get_translation("youtube_label", lang), left_layout)


        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet("color: #333; margin: 6px 0;")
        left_layout.addWidget(sep1)
        section_label(get_translation("general_section", lang), left_layout, "settings.svg")

        self.glass_check = QCheckBox(get_translation("glassmorphism_label", lang))
        self.glass_check.setChecked(self.settings_manager.settings.get("glassmorphism", True))
        self.glass_check.setToolTip(get_translation("glassmorphism_tooltip", lang))
        left_layout.addWidget(self.glass_check)

        # 1. Opacidade do Fundo (Fundo Escuro Translúcido)
        left_layout.addWidget(QLabel(get_translation("bg_opacity_label", lang)))
        bg_op_row = QHBoxLayout()
        self.bg_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_opacity_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.bg_opacity_slider.installEventFilter(_wheel_ignore)
        self.bg_opacity_slider.setRange(0, 100)
        current_bg_op = int(self.settings_manager.settings.get("bg_opacity", self.settings_manager.settings.get("opacity", 0.75)) * 100)
        self.bg_opacity_slider.setValue(current_bg_op)
        self.bg_opacity_val_label = QLabel(f"{self.bg_opacity_slider.value()}%")
        self.bg_opacity_val_label.setFixedWidth(36)
        self.bg_opacity_slider.valueChanged.connect(lambda v: self.bg_opacity_val_label.setText(f"{v}%"))
        bg_op_row.addWidget(self.bg_opacity_slider); bg_op_row.addWidget(self.bg_opacity_val_label)
        left_layout.addLayout(bg_op_row)

        # 2. Opacidade do Texto / Mensagens
        left_layout.addWidget(QLabel(get_translation("text_opacity_label", lang)))
        txt_op_row = QHBoxLayout()
        self.text_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_opacity_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.text_opacity_slider.installEventFilter(_wheel_ignore)
        self.text_opacity_slider.setRange(20, 100)
        current_txt_op = int(self.settings_manager.settings.get("text_opacity", 1.0) * 100)
        self.text_opacity_slider.setValue(current_txt_op)
        self.text_opacity_val_label = QLabel(f"{self.text_opacity_slider.value()}%")
        self.text_opacity_val_label.setFixedWidth(36)
        self.text_opacity_slider.valueChanged.connect(lambda v: self.text_opacity_val_label.setText(f"{v}%"))
        txt_op_row.addWidget(self.text_opacity_slider); txt_op_row.addWidget(self.text_opacity_val_label)
        left_layout.addLayout(txt_op_row)

        left_layout.addWidget(QLabel(get_translation("delay_label", lang)))
        dl_row = QHBoxLayout()
        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.delay_slider.installEventFilter(_wheel_ignore)
        self.delay_slider.setRange(0, 50)
        current_delay = float(self.settings_manager.settings.get("message_delay", 0))
        self.delay_slider.setValue(int(current_delay * 10))
        self.delay_val_label = QLabel(f"{current_delay:.1f}s")
        self.delay_val_label.setFixedWidth(36)
        self.delay_slider.valueChanged.connect(lambda v: self.delay_val_label.setText(f"{v/10.0:.1f}s"))
        dl_row.addWidget(self.delay_slider); dl_row.addWidget(self.delay_val_label)
        left_layout.addLayout(dl_row)

        sep_tts = QFrame(); sep_tts.setFrameShape(QFrame.Shape.HLine); sep_tts.setStyleSheet("color: #333; margin: 6px 0;")
        left_layout.addWidget(sep_tts)
        section_label(get_translation("tts_section", lang), left_layout, "settings.svg")

        self.tts_enable_check = QCheckBox(get_translation("tts_enable_label", lang))
        self.tts_enable_check.setChecked(self.settings_manager.settings.get("tts_enabled", True))
        left_layout.addWidget(self.tts_enable_check)

        # --- Seletor de Motor de Voz ---
        engine_row = QHBoxLayout()
        engine_lbl = QLabel(get_translation("tts_engine_label", lang))
        engine_lbl.setStyleSheet("font-weight: bold; color: #ccc;")
        engine_row.addWidget(engine_lbl)
        self.combo_tts_engine = QComboBox()
        self.combo_tts_engine.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.combo_tts_engine.installEventFilter(_wheel_ignore)
        self.combo_tts_engine.addItem(get_translation("tts_engine_edge", lang), "edge")
        self.combo_tts_engine.addItem(get_translation("tts_engine_google", lang), "google")
        current_engine = self.settings_manager.settings.get("tts_engine", "edge")
        idx_engine = self.combo_tts_engine.findData(current_engine)
        if idx_engine >= 0:
            self.combo_tts_engine.setCurrentIndex(idx_engine)
        engine_row.addWidget(self.combo_tts_engine)
        left_layout.addLayout(engine_row)

        self._google_info_label = QLabel(get_translation("google_tts_info", lang))
        self._google_info_label.setStyleSheet("color: #facc15; font-size: 10px; margin-left: 4px;")
        self._google_info_label.setWordWrap(True)
        left_layout.addWidget(self._google_info_label)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel(get_translation("tts_volume_label", lang)))
        self.tts_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_volume_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tts_volume_slider.installEventFilter(_wheel_ignore)
        self.tts_volume_slider.setRange(0, 100)
        current_vol = self.settings_manager.settings.get("tts_volume", 100)
        self.tts_volume_slider.setValue(int(current_vol))
        self.tts_volume_val_label = QLabel(f"{current_vol}%")
        self.tts_volume_val_label.setFixedWidth(36)
        self.tts_volume_slider.valueChanged.connect(lambda v: self.tts_volume_val_label.setText(f"{v}%"))
        vol_row.addWidget(self.tts_volume_slider); vol_row.addWidget(self.tts_volume_val_label)
        left_layout.addLayout(vol_row)

        self.voices_list = [
            (get_translation("voice_antonio", lang), "pt-BR-AntonioNeural"),
            (get_translation("voice_francisca", lang), "pt-BR-FranciscaNeural"),
            (get_translation("voice_thalita", lang), "pt-BR-ThalitaMultilingualNeural")
        ]
        
        def create_voice_combo(platform_name, config_key, default_voice):
            # Encapsula em QWidget para poder mostrar/ocultar o bloco inteiro
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)

            # Checkbox da plataforma
            check_key = f"tts_enabled_{platform_name.lower()}"
            check = QCheckBox(platform_name)
            check.setChecked(self.settings_manager.settings.get(check_key, True))
            check.setFixedWidth(85)
            row.addWidget(check)
            setattr(self, f"check_{platform_name.lower()}", check)

            combo = QComboBox()
            combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            combo.installEventFilter(_wheel_ignore)
            for name, code in self.voices_list:
                combo.addItem(name, code)

            current_voice = self.settings_manager.settings.get(config_key, default_voice)
            index = combo.findData(current_voice)
            if index >= 0:
                combo.setCurrentIndex(index)

            row.addWidget(combo)
            return combo, container

        self.combo_twitch, row_tw = create_voice_combo("Twitch", "tts_voice_twitch", "pt-BR-AntonioNeural")
        self.combo_tiktok, row_tt = create_voice_combo("TikTok", "tts_voice_tiktok", "pt-BR-FranciscaNeural")
        self.combo_kick, row_kk = create_voice_combo("Kick", "tts_voice_kick", "pt-BR-ThalitaMultilingualNeural")
        self.combo_youtube, row_yt = create_voice_combo("YouTube", "tts_voice_youtube", "pt-BR-AntonioNeural")

        self._voice_combo_rows = [row_tw, row_tt, row_kk, row_yt]

        left_layout.addWidget(row_tw)
        left_layout.addWidget(row_tt)
        left_layout.addWidget(row_kk)
        left_layout.addWidget(row_yt)

        # Conecta o motor ao show/hide dos combos e aviso
        def on_engine_changed(_idx):
            is_google = self.combo_tts_engine.currentData() == "google"
            self._google_info_label.setVisible(is_google)
            for w in self._voice_combo_rows:
                w.setVisible(not is_google)

        self.combo_tts_engine.currentIndexChanged.connect(on_engine_changed)

        # Aplica visibilidade inicial
        _init_google = current_engine == "google"
        self._google_info_label.setVisible(_init_google)
        for _w in self._voice_combo_rows:
            _w.setVisible(not _init_google)



        left_layout.addWidget(QLabel(get_translation("language_label", lang)))
        self.lang_combo = QComboBox()
        self.lang_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.lang_combo.installEventFilter(_wheel_ignore)
        self.lang_codes = get_available_languages()
        self.lang_combo.addItems([get_language_display_name(c) for c in self.lang_codes])
        current_index = self.lang_codes.index(lang) if lang in self.lang_codes else 0
        self.lang_combo.setCurrentIndex(current_index)
        left_layout.addWidget(self.lang_combo)

        left_layout.addStretch()
        
        # Scroll area que envolve o conteúdo esquerdo
        left_scroll = QScrollArea()
        left_scroll.setObjectName("panel")
        left_scroll.setWidget(left_content)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setStyleSheet("""
            QScrollArea#panel {
                background-color: #242424;
                border: 1px solid #333;
                border-radius: 8px;
            }
            QWidget#left_content {
                background-color: #242424;
            }
            QScrollBar:vertical {
                background: #2e2e2e;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #007acc;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        panels_layout.addWidget(left_scroll, 1)

        # ── PAINEL DIREITO: Aparência + Blacklist + Hotkeys ──────────────────
        right_content = QWidget()
        right_content.setObjectName("right_content")
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(6)

        section_label(get_translation("appearance_section", lang), right_layout, "icon_palette.svg")

        right_layout.addWidget(QLabel(get_translation("font_label", lang)))
        self.font_combo = QComboBox()
        self.font_options = [
            "Segoe UI Variable Display", "Inter", "Roboto", "Montserrat",
            "Orbitron", "Kanit", "Rajdhani", "Bebas Neue", "Chakra Petch"
        ]
        self.font_combo.addItems(self.font_options)
        current_font = self.settings_manager.settings.get("font_family", "Segoe UI Variable Display")
        if current_font in self.font_options:
            self.font_combo.setCurrentIndex(self.font_options.index(current_font))
        else:
            self.font_combo.addItem(current_font)
            self.font_combo.setCurrentIndex(self.font_combo.count() - 1)
        right_layout.addWidget(self.font_combo)

        sz_row = QHBoxLayout()
        sz_row.addWidget(QLabel(get_translation("font_size_label", lang)))
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(8, 48)
        current_size = self.settings_manager.settings.get("font_size", 11)
        self.font_size_slider.setValue(int(current_size))
        self.size_value_label = QLabel(f"{current_size}px")
        self.size_value_label.setFixedWidth(36)
        self.font_size_slider.valueChanged.connect(lambda v: self.size_value_label.setText(f"{v}px"))
        sz_row.addWidget(self.font_size_slider); sz_row.addWidget(self.size_value_label)
        right_layout.addLayout(sz_row)

        self.platform_colors = self.settings_manager.settings.get("platform_colors", {}).copy()
        for platform in ["twitch", "tiktok", "kick", "youtube"]:
            color_row = QHBoxLayout()
            color_row.addWidget(QLabel(get_translation(f"{platform}_color_label", lang)))
            color_row.addStretch()
            color_preview = QFrame()
            color_preview.setFixedSize(22, 22)
            current_color = self.platform_colors.get(platform, "#555")
            color_preview.setStyleSheet(f"background-color: {current_color}; border-radius: 4px; border: 1px solid #777;")
            color_btn = QPushButton(get_translation("pick_color", lang))
            color_btn.setFixedHeight(30)
            color_btn.clicked.connect(lambda checked, p=platform, cp=color_preview: self.pick_platform_color(p, cp))
            color_row.addWidget(color_btn); color_row.addWidget(color_preview)
            right_layout.addLayout(color_row)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet("color: #333; margin: 6px 0;")
        right_layout.addWidget(sep2)
        section_label(get_translation("blacklist_label", lang), right_layout, "icon_shield.svg")

        self.tags_container = HeightAwareWidget()
        self.tags_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tags_container.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; border: 1px solid #444;")
        self.tags_container.setMinimumHeight(40)
        
        self.tags_layout = FlowLayout(self.tags_container, 5, 5)
        
        self.bl_scroll = QScrollArea()
        self.bl_scroll.setWidgetResizable(True)
        self.bl_scroll.setWidget(self.tags_container)
        self.bl_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.bl_scroll.setMinimumHeight(46)
        self.bl_scroll.setMaximumHeight(150)
        right_layout.addWidget(self.bl_scroll)

        self.blacklist_input = QLineEdit()
        self.blacklist_input.setPlaceholderText(get_translation("blacklist_placeholder", lang))
        self.blacklist_input.keyPressEvent = self.handle_blacklist_key
        right_layout.addWidget(self.blacklist_input)

        initial_blacklist = self.settings_manager.settings.get("blacklist", [])
        for word in initial_blacklist:
            self.add_tag(word)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine); sep3.setStyleSheet("color: #333; margin: 6px 0;")
        right_layout.addWidget(sep3)
        section_label(get_translation("hotkeys_section", lang), right_layout, "icon_keyboard.svg")

        hint = QLabel(get_translation("hotkeys_hint", lang))
        hint.setStyleSheet("color: #777; font-size: 10px; font-weight: normal; margin-top: 0;")
        right_layout.addWidget(hint)

        def create_info_btn(info_key):
            btn = QPushButton("?")
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { 
                    background: #555; color: white; font-weight: bold; 
                    border-radius: 10px; border: none; 
                    font-size: 13px; font-family: Arial, sans-serif;
                    padding: 0px; margin: 0px; text-align: center;
                }
                QPushButton:hover { background: #007acc; }
            """)
            btn.setToolTip(get_translation(info_key, lang))
            
            def force_show_tooltip():
                from PyQt6.QtWidgets import QToolTip
                from PyQt6.QtGui import QCursor
                QToolTip.showText(QCursor.pos(), btn.toolTip(), btn)
                
            btn.clicked.connect(force_show_tooltip)
            return btn

        hk1 = QHBoxLayout()
        icon_hk1_path = resource_path("assets/show.svg")
        icon_lbl1 = QLabel()
        icon_lbl1.setPixmap(QIcon(icon_hk1_path).pixmap(14, 14))
        hk1.addWidget(icon_lbl1)
        hk1.addWidget(QLabel(get_translation("hotkey_toggle", lang)))
        hk1.addWidget(create_info_btn("info_toggle"))
        self.hotkey_toggle_field = HotkeyField(lang=lang)
        self.hotkey_toggle_field.setText(self.settings_manager.settings.get("hotkey_toggle_visibility", "ctrl+shift+h"))
        hk1.addWidget(self.hotkey_toggle_field)
        right_layout.addLayout(hk1)

        hk2 = QHBoxLayout()
        icon_hk2_path = resource_path("assets/clear.svg")
        icon_lbl2 = QLabel()
        icon_lbl2.setPixmap(QIcon(icon_hk2_path).pixmap(14, 14))
        hk2.addWidget(icon_lbl2)
        hk2.addWidget(QLabel(get_translation("hotkey_clear", lang)))
        hk2.addWidget(create_info_btn("info_clear"))
        self.hotkey_clear_field = HotkeyField(lang=lang)
        self.hotkey_clear_field.setText(self.settings_manager.settings.get("hotkey_clear_chat", "ctrl+shift+c"))
        hk2.addWidget(self.hotkey_clear_field)
        right_layout.addLayout(hk2)

        hk3 = QHBoxLayout()
        # You can use a mouse icon if available, else pin or show
        icon_hk3_path = resource_path("assets/pin.svg") 
        icon_lbl3 = QLabel()
        icon_lbl3.setPixmap(QIcon(icon_hk3_path).pixmap(14, 14))
        hk3.addWidget(icon_lbl3)
        hk3.addWidget(QLabel(get_translation("hotkey_clickthrough", lang)))
        hk3.addWidget(create_info_btn("info_clickthrough"))
        self.hotkey_clickthrough_field = HotkeyField(lang=lang)
        self.hotkey_clickthrough_field.setText(self.settings_manager.settings.get("hotkey_clickthrough", "ctrl+alt+t"))
        hk3.addWidget(self.hotkey_clickthrough_field)
        right_layout.addLayout(hk3)

        sep4 = QFrame(); sep4.setFrameShape(QFrame.Shape.HLine); sep4.setStyleSheet("color: #333; margin: 6px 0;")
        right_layout.addWidget(sep4)

        # Botão de Login do TikTok (para lives +18)
        self.tiktok_session_id = self.settings_manager.settings.get("tiktok_session_id", "")
        tiktok_login_row = QHBoxLayout()
        self.tiktok_login_status_lbl = QLabel()
        self.tiktok_login_btn = QPushButton()
        self._update_tiktok_login_ui()
        self.tiktok_login_btn.clicked.connect(self._handle_tiktok_login_click)
        tiktok_login_row.addWidget(self.tiktok_login_status_lbl)
        tiktok_login_row.addStretch()
        tiktok_login_row.addWidget(self.tiktok_login_btn)
        right_layout.addLayout(tiktok_login_row)

        right_layout.addStretch()

        right_scroll = QScrollArea()
        right_scroll.setObjectName("panel")
        right_scroll.setWidget(right_content)
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setStyleSheet("""
            QScrollArea#panel {
                background-color: #242424;
                border: 1px solid #333;
                border-radius: 8px;
            }
            QWidget#right_content {
                background-color: #242424;
            }
            QScrollBar:vertical {
                background: #2e2e2e;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #007acc;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        panels_layout.addWidget(right_scroll, 1)
        self.layout.addLayout(panels_layout)

        # ── BOTÕES INFERIORES (largura total) ─────────────────────────────────
        self.save_btn = QPushButton(get_translation("save_btn", lang))
        self.save_btn.setObjectName("save_btn")
        self.save_btn.clicked.connect(self.save)
        self.layout.addWidget(self.save_btn)

        self.quit_app_btn = QPushButton(get_translation("quit_btn", lang))
        self.quit_app_btn.setObjectName("quit_btn")
        self.quit_app_btn.clicked.connect(self.confirm_quit)
        self.layout.addWidget(self.quit_app_btn)



    def _update_tiktok_login_ui(self):
        """Atualiza o visual do botão e label de acordo com o estado de login."""
        lang = self.settings_manager.settings.get("language", "pt-br")
        if self.tiktok_session_id:
            self.tiktok_login_status_lbl.setText(get_translation("tiktok_connected_status", lang))
            self.tiktok_login_status_lbl.setStyleSheet("color: #00cc66; font-size: 10px; font-weight: bold;")
            self.tiktok_login_btn.setText(get_translation("tiktok_connected_btn", lang))
            self.tiktok_login_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a7a45;
                    color: #aaffcc; font-weight: bold;
                    border-radius: 5px; padding: 6px 12px;
                    font-size: 11px; border: 1px solid #00cc66;
                }
                QPushButton:hover { background-color: #c0392b; color: white; }
            """)
        else:
            self.tiktok_login_status_lbl.setText(get_translation("tiktok_not_connected_status", lang))
            self.tiktok_login_status_lbl.setStyleSheet("color: #ff8888; font-size: 10px;")
            self.tiktok_login_btn.setText(get_translation("tiktok_login_btn", lang))
            self.tiktok_login_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fe2c55;
                    color: white; font-weight: bold;
                    border-radius: 5px; padding: 6px 12px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #ff5577; }
            """)

    def _handle_tiktok_login_click(self):
        """Gerencia o clique no botão: se já conectado, pergunta se quer desconectar."""
        lang = self.settings_manager.settings.get("language", "pt-br")
        if self.tiktok_session_id:
            reply = QMessageBox.question(
                self,
                get_translation("tiktok_disconnect_title", lang),
                get_translation("tiktok_disconnect_msg", lang),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.tiktok_session_id = ""
                self.settings_manager.settings["tiktok_session_id"] = ""
                self.settings_manager.save_settings()
                self._update_tiktok_login_ui()
        else:
            self._open_tiktok_login()

    def _open_tiktok_login(self):
        """Mostra aviso e abre o mini-navegador para o usuário fazer login no TikTok."""
        lang = self.settings_manager.settings.get("language", "pt-br")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(get_translation("tiktok_why_login_title", lang))
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(get_translation("tiktok_why_login_text", lang))
        btn_continuar = msg_box.addButton(get_translation("continue_btn", lang), QMessageBox.ButtonRole.AcceptRole)
        btn_cancelar = msg_box.addButton(get_translation("cancel_btn", lang), QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_continuar:
            try:
                from ui.tiktok_login_dialog import TikTokLoginDialog
                dialog = TikTokLoginDialog(self, lang=lang)
                dialog.login_success.connect(self._on_tiktok_login_success)
                dialog.exec()
            except ImportError as e:
                QMessageBox.warning(self, "Error", get_translation("tiktok_login_error_webengine", lang, error=str(e)))

    def _on_tiktok_login_success(self, session_id):
        """Chamado quando o login é detectado — salva o sessionid imediatamente."""
        lang = self.settings_manager.settings.get("language", "pt-br")
        self.tiktok_session_id = session_id
        self.settings_manager.settings["tiktok_session_id"] = session_id
        
        self.settings_manager.save_settings()
        self._update_tiktok_login_ui()
        QMessageBox.information(self, "OK", get_translation("tiktok_login_success", lang), QMessageBox.StandardButton.Ok)

    def confirm_quit(self):
        lang = self.settings_manager.settings.get("language", "pt-br")
        reply = QMessageBox.question(self, get_translation("confirm_quit_title", lang), 
            get_translation("confirm_quit_msg", lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()

    def _add_config_field_to(self, key, label_text, target_layout):
        lang = self.settings_manager.settings.get("language", "pt-br")
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(120)
        line_edit = QLineEdit()
        line_edit.setMinimumWidth(180)
        line_edit.setSizePolicy(line_edit.sizePolicy().horizontalPolicy(), line_edit.sizePolicy().verticalPolicy())
        # Dica visual de formato esperado para cada plataforma (sem @ para evitar erro)
        placeholders = {
            "tiktok":   get_translation("placeholder_username", lang),
            "twitch":   get_translation("placeholder_username", lang),
            "kick":     get_translation("placeholder_username", lang),
            "youtube":  get_translation("placeholder_username", lang),
        }
        if key in placeholders:
            line_edit.setPlaceholderText(placeholders[key])
        saved_val = self.settings_manager.settings.get(key, "")
        # Garantir que valor salvo do TikTok não tem @ (limpeza retroativa)
        if key == "tiktok" and saved_val.startswith("@"):
            saved_val = saved_val.lstrip("@")
        line_edit.setText(saved_val)
        setattr(self, f"{key}_input", line_edit)
        
        # Botão de reconectar
        reconnect_btn = QPushButton()
        reconnect_icon_path = resource_path("assets/reconnect.svg")
        reconnect_btn.setIcon(QIcon(reconnect_icon_path))
        reconnect_btn.setToolTip(get_translation("reconnect_tooltip", lang, label=label_text))
        reconnect_btn.setFixedSize(22, 22)
        reconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reconnect_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { 
                background-color: #333; 
            }
        """)
        reconnect_btn.clicked.connect(lambda checked, p=key: self._reconnect_platform(p))
        
        # LED de Status (CSS)
        status_led = QFrame()
        status_led.setFixedSize(12, 12)
        status_led.setObjectName(f"status_{key}")
        status_led.setStyleSheet("background-color: #555; border-radius: 6px;")
        self.status_labels[key] = status_led
        
        h_layout.addWidget(label)
        h_layout.addWidget(line_edit)
        h_layout.addWidget(reconnect_btn)
        h_layout.addWidget(status_led)
        target_layout.addLayout(h_layout)
        
        # Atualizar status inicial
        if self.chat_manager:
            if self.chat_manager.statuses.get(key):
                status_led.setStyleSheet("background-color: #00ff00; border-radius: 6px; border: 1px solid #00aa00;")
            else:
                status_led.setStyleSheet("background-color: #ff0000; border-radius: 6px; border: 1px solid #aa0000;")

    def _reconnect_platform(self, platform):
        # Salvar as configs atuais do input para garantir que vai conectar com o username digitado
        username_input = getattr(self, f"{platform}_input").text().strip()
        # TikTok: remover @ automaticamente se o usuário digitou (ex: @furiousofnight -> furiousofnight)
        if platform == "tiktok" and username_input.startswith("@"):
            username_input = username_input.lstrip("@")
            getattr(self, f"{platform}_input").setText(username_input)
        self.settings_manager.settings[platform] = username_input
        self.settings_manager.save_settings()
        
        if self.chat_manager:
            self.chat_manager.restart_platform(platform)

    def update_platform_status(self, platform, connected):
        if platform in self.status_labels:
            led = self.status_labels[platform]
            if connected:
                led.setStyleSheet("background-color: #00ff00; border-radius: 6px; border: 1px solid #00aa00;")
            else:
                led.setStyleSheet("background-color: #ff0000; border-radius: 6px; border: 1px solid #aa0000;")

    def handle_blacklist_key(self, event):
        # Captura Espaço, Enter ou Vírgula para criar a tag
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Comma):
            text = self.blacklist_input.text().strip().replace(",", "")
            if text:
                self.add_tag(text)
                self.blacklist_input.clear()
            return # Bloqueia a digitação do espaço/enter no campo
        
        # Comportamento padrão para outras teclas
        QLineEdit.keyPressEvent(self.blacklist_input, event)

    def add_tag(self, text):
        if text in self.tags: return
        tag = TagWidget(text)
        tag.removed.connect(self.remove_tag)
        self.tags_layout.addWidget(tag)
        self.tags.append(text)

    def remove_tag(self, text):
        if text in self.tags:
            self.tags.remove(text)
            # Achar o widget e deletar
            for i in range(self.tags_layout.count()):
                item = self.tags_layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if isinstance(w, TagWidget) and w.text == text:
                        w.deleteLater()
                        break

    def pick_platform_color(self, platform, preview_widget):
        initial_color = QColor(self.platform_colors.get(platform, "#555"))
        color = QColorDialog.getColor(initial_color, self, get_translation("pick_color", self.settings_manager.settings.get("language", "pt-br")))
        
        if color.isValid():
            hex_color = color.name().upper()
            self.platform_colors[platform] = hex_color
            preview_widget.setStyleSheet(f"background-color: {hex_color}; border-radius: 4px; border: 1px solid #777;")

    def save(self):
        self.settings_manager.settings["twitch"] = self.twitch_input.text().strip()
        self.settings_manager.settings["tiktok"] = self.tiktok_input.text().strip()
        self.settings_manager.settings["kick"] = self.kick_input.text().strip()
        self.settings_manager.settings["youtube"] = self.youtube_input.text().strip()
        
        bg_op = self.bg_opacity_slider.value() / 100.0
        self.settings_manager.settings["bg_opacity"] = bg_op
        self.settings_manager.settings["opacity"] = bg_op # Compatibilidade
        
        text_op = self.text_opacity_slider.value() / 100.0
        self.settings_manager.settings["text_opacity"] = text_op
        
        self.settings_manager.settings["glassmorphism"] = self.glass_check.isChecked()
        self.settings_manager.settings["message_delay"] = self.delay_slider.value() / 10.0
        
        self.settings_manager.settings["tts_enabled"] = self.tts_enable_check.isChecked()
        self.settings_manager.settings["tts_volume"] = self.tts_volume_slider.value()
        self.settings_manager.settings["tts_engine"] = self.combo_tts_engine.currentData()
        
        self.settings_manager.settings["tts_enabled_twitch"] = self.check_twitch.isChecked()
        self.settings_manager.settings["tts_enabled_tiktok"] = self.check_tiktok.isChecked()
        self.settings_manager.settings["tts_enabled_kick"] = self.check_kick.isChecked()
        self.settings_manager.settings["tts_enabled_youtube"] = self.check_youtube.isChecked()
        
        self.settings_manager.settings["tts_voice_twitch"] = self.combo_twitch.currentData()
        self.settings_manager.settings["tts_voice_tiktok"] = self.combo_tiktok.currentData()
        self.settings_manager.settings["tts_voice_kick"] = self.combo_kick.currentData()
        self.settings_manager.settings["tts_voice_youtube"] = self.combo_youtube.currentData()
        
        current_lang_index = self.lang_combo.currentIndex()
        self.settings_manager.settings["language"] = self.lang_codes[current_lang_index] if current_lang_index < len(self.lang_codes) else "pt-br"
        
        self.settings_manager.settings["font_family"] = self.font_combo.currentText()
        self.settings_manager.settings["font_size"] = self.font_size_slider.value()
        self.settings_manager.settings["platform_colors"] = self.platform_colors
        
        self.settings_manager.settings["blacklist"] = list(self.tags)
        
        # Salva hotkeys
        self.settings_manager.settings["hotkey_toggle_visibility"] = self.hotkey_toggle_field.text().strip() or "ctrl+shift+h"
        self.settings_manager.settings["hotkey_clear_chat"] = self.hotkey_clear_field.text().strip() or "ctrl+shift+c"
        self.settings_manager.settings["hotkey_clickthrough"] = self.hotkey_clickthrough_field.text().strip() or "ctrl+alt+t"
        
        self.settings_manager.save_settings()
        
        # Ao salvar, limpa toda a fila de voz antiga para aplicar as configurações apenas em novas mensagens
        if hasattr(self.main_window, "tts_manager"):
            self.main_window.tts_manager.clear_queue()
            
        self.accept()
