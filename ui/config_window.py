from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QSlider, QComboBox, QCheckBox, QPlainTextEdit, QWidget, QFrame, QScrollArea, QMessageBox, QColorDialog
from PyQt6.QtGui import QColor, QIcon, QFont, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from utils.translations import get_translation, get_available_languages, get_language_display_name
from utils.resource_path import resource_path
import os

# Helper para recursos



class HotkeyField(QLineEdit):
    """Campo que captura o atalho de teclado quando o usuário pressiona as teclas."""
    def __init__(self, placeholder="Clique e pressione as teclas...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
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
        self.setPlaceholderText("⏳ Pressione as teclas...")
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
            self.setPlaceholderText("Clique e pressione as teclas...")
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
        self.setPlaceholderText("Clique e pressione as teclas...")
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

class FlowLayout(QVBoxLayout):
    # Simplificação: Usaremos um QHBoxLayout que permite Wrap ou apenas uma lista vertical limpa
    # Mas para "profisisonal", vamos fazer um container de tags real.
    pass

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
        self.setFixedWidth(780)
        self.setMinimumHeight(520)
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

        # ── PAINEL ESQUERDO: Conexões + Geral ────────────────────────────────
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(6)

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

        section_label("Conexões", left_layout, "icon_link.svg")
        self._add_config_field_to("twitch", get_translation("twitch_label", lang), left_layout)
        self._add_config_field_to("tiktok", get_translation("tiktok_label", lang), left_layout)
        self._add_config_field_to("kick",   get_translation("kick_label", lang),   left_layout)


        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet("color: #333; margin: 6px 0;")
        left_layout.addWidget(sep1)
        section_label("Geral", left_layout, "settings.svg")

        self.glass_check = QCheckBox(get_translation("glassmorphism_label", lang))
        self.glass_check.setChecked(self.settings_manager.settings.get("glassmorphism", True))
        left_layout.addWidget(self.glass_check)

        left_layout.addWidget(QLabel(get_translation("opacity_label", lang)))
        op_row = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(self.settings_manager.settings.get("opacity", 0.85) * 100))
        self.opacity_val_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_val_label.setFixedWidth(36)
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_val_label.setText(f"{v}%"))
        op_row.addWidget(self.opacity_slider); op_row.addWidget(self.opacity_val_label)
        left_layout.addLayout(op_row)

        left_layout.addWidget(QLabel(get_translation("delay_label", lang)))
        dl_row = QHBoxLayout()
        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
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
        section_label("Voz do Bot (TTS)", left_layout, "settings.svg")

        self.tts_enable_check = QCheckBox("Ativar Leitura de Chat (TTS)")
        self.tts_enable_check.setChecked(self.settings_manager.settings.get("tts_enabled", True))
        left_layout.addWidget(self.tts_enable_check)
        
        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Volume da Voz"))
        self.tts_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_volume_slider.setRange(0, 100)
        current_vol = self.settings_manager.settings.get("tts_volume", 100)
        self.tts_volume_slider.setValue(int(current_vol))
        self.tts_volume_val_label = QLabel(f"{current_vol}%")
        self.tts_volume_val_label.setFixedWidth(36)
        self.tts_volume_slider.valueChanged.connect(lambda v: self.tts_volume_val_label.setText(f"{v}%"))
        vol_row.addWidget(self.tts_volume_slider); vol_row.addWidget(self.tts_volume_val_label)
        left_layout.addLayout(vol_row)

        self.voices_list = [
            ("Antônio (Masculino)", "pt-BR-AntonioNeural"),
            ("Francisca (Feminina)", "pt-BR-FranciscaNeural"),
            ("Thalita (Feminina)", "pt-BR-ThalitaMultilingualNeural")
        ]
        
        def create_voice_combo(platform_name, config_key, default_voice):
            row = QHBoxLayout()
            
            # Checkbox da plataforma
            check_key = f"tts_enabled_{platform_name.lower()}"
            check = QCheckBox(platform_name)
            check.setChecked(self.settings_manager.settings.get(check_key, True))
            check.setFixedWidth(65)
            row.addWidget(check)
            setattr(self, f"check_{platform_name.lower()}", check)
            
            combo = QComboBox()
            for name, code in self.voices_list:
                combo.addItem(name, code)
            
            current_voice = self.settings_manager.settings.get(config_key, default_voice)
            index = combo.findData(current_voice)
            if index >= 0:
                combo.setCurrentIndex(index)
                
            row.addWidget(combo)
            return combo, row
            
        self.combo_twitch, row_tw = create_voice_combo("Twitch", "tts_voice_twitch", "pt-BR-AntonioNeural")
        self.combo_tiktok, row_tt = create_voice_combo("TikTok", "tts_voice_tiktok", "pt-BR-FranciscaNeural")
        self.combo_kick, row_kk = create_voice_combo("Kick", "tts_voice_kick", "pt-BR-ThalitaMultilingualNeural")
        
        left_layout.addLayout(row_tw)
        left_layout.addLayout(row_tt)
        left_layout.addLayout(row_kk)

        left_layout.addWidget(QLabel(get_translation("language_label", lang)))
        self.lang_combo = QComboBox()
        self.lang_codes = get_available_languages()
        self.lang_combo.addItems([get_language_display_name(c) for c in self.lang_codes])
        current_index = self.lang_codes.index(lang) if lang in self.lang_codes else 0
        self.lang_combo.setCurrentIndex(current_index)
        left_layout.addWidget(self.lang_combo)

        left_layout.addStretch()
        panels_layout.addWidget(left_panel, 1)

        # ── PAINEL DIREITO: Aparência + Blacklist + Hotkeys ──────────────────
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
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
        for platform in ["twitch", "tiktok", "kick"]:
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

        self.tags_container = QFrame()
        self.tags_container.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; border: 1px solid #444;")
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(5, 5, 5, 5)
        self.tags_layout.setSpacing(5)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bl_scroll = QScrollArea()
        bl_scroll.setWidgetResizable(True)
        bl_scroll.setWidget(self.tags_container)
        bl_scroll.setFixedHeight(46)
        right_layout.addWidget(bl_scroll)

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

        hk1 = QHBoxLayout()
        icon_hk1_path = resource_path("assets/show.svg")
        icon_lbl1 = QLabel()
        icon_lbl1.setPixmap(QIcon(icon_hk1_path).pixmap(14, 14))
        hk1.addWidget(icon_lbl1)
        hk1.addWidget(QLabel(get_translation("hotkey_toggle", lang)))
        self.hotkey_toggle_field = HotkeyField()
        self.hotkey_toggle_field.setText(self.settings_manager.settings.get("hotkey_toggle_visibility", "ctrl+shift+h"))
        hk1.addWidget(self.hotkey_toggle_field)
        right_layout.addLayout(hk1)

        hk2 = QHBoxLayout()
        icon_hk2_path = resource_path("assets/clear.svg")
        icon_lbl2 = QLabel()
        icon_lbl2.setPixmap(QIcon(icon_hk2_path).pixmap(14, 14))
        hk2.addWidget(icon_lbl2)
        hk2.addWidget(QLabel(get_translation("hotkey_clear", lang)))
        self.hotkey_clear_field = HotkeyField()
        self.hotkey_clear_field.setText(self.settings_manager.settings.get("hotkey_clear_chat", "ctrl+shift+c"))
        hk2.addWidget(self.hotkey_clear_field)
        right_layout.addLayout(hk2)

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
        panels_layout.addWidget(right_panel, 1)
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
        if self.tiktok_session_id:
            self.tiktok_login_status_lbl.setText("TikTok: Conectado")
            self.tiktok_login_status_lbl.setStyleSheet("color: #00cc66; font-size: 10px; font-weight: bold;")
            self.tiktok_login_btn.setText("Conectado")
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
            self.tiktok_login_status_lbl.setText("TikTok: Nao conectado")
            self.tiktok_login_status_lbl.setStyleSheet("color: #ff8888; font-size: 10px;")
            self.tiktok_login_btn.setText("Fazer Login no TikTok")
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
        if self.tiktok_session_id:
            reply = QMessageBox.question(
                self,
                "Desconectar do TikTok?",
                "Você já está conectado.\n\nDeseja remover a conta e desconectar?\n(Lives +18 perderão o horario real)",
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
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Por que fazer login no TikTok?")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(
            "<b>O login no TikTok é opcional.</b><br><br>"
            "Ele é necessário <b>apenas</b> se você quiser que o cronômetro mostre o tempo total da live "
            "em transmissões com restrição de idade (+18) ou caso você conecte atrasado.<br><br>"
            "Sem o login, o relógio do chat começará sempre do <b>00:00:00</b> no momento em que você conectar.<br><br>"
            "<b>Recomendado:</b> use uma conta secundária do TikTok para login, nunca a conta principal.<br><br>"
            "<i>🔒 <b>Sua Privacidade:</b> Não salvamos sua senha. Os dados de login ficam apenas neste computador, em um arquivo local.</i>"
        )
        btn_continuar = msg_box.addButton("Continuar", QMessageBox.ButtonRole.AcceptRole)
        btn_cancelar = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_continuar:
            try:
                from ui.tiktok_login_dialog import TikTokLoginDialog
                dialog = TikTokLoginDialog(self)
                dialog.login_success.connect(self._on_tiktok_login_success)
                dialog.exec()
            except ImportError as e:
                QMessageBox.warning(self, "Erro", f"PyQt6-WebEngine nao esta instalado.\nInstale com: pip install PyQt6-WebEngine\n\n{e}")

    def _on_tiktok_login_success(self, session_id):
        """Chamado quando o login é detectado — salva o sessionid imediatamente."""
        self.tiktok_session_id = session_id
        self.settings_manager.settings["tiktok_session_id"] = session_id
        
        self.settings_manager.save_settings()
        self._update_tiktok_login_ui()
        QMessageBox.information(self, "Sucesso!", "Login no TikTok realizado com sucesso!\nSuas lives +18 agora vao mostrar o horario real.", QMessageBox.StandardButton.Ok)

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
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setText(self.settings_manager.settings.get(key, ""))
        setattr(self, f"{key}_input", line_edit)
        
        # Botão de reconectar
        reconnect_btn = QPushButton()
        reconnect_icon_path = resource_path("assets/reconnect.svg")
        reconnect_btn.setIcon(QIcon(reconnect_icon_path))
        reconnect_btn.setToolTip(f"Reconectar {label_text}")
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
        
        self.settings_manager.settings["opacity"] = self.opacity_slider.value() / 100.0
        self.settings_manager.settings["glassmorphism"] = self.glass_check.isChecked()
        self.settings_manager.settings["message_delay"] = self.delay_slider.value() / 10.0
        
        self.settings_manager.settings["tts_enabled"] = self.tts_enable_check.isChecked()
        self.settings_manager.settings["tts_volume"] = self.tts_volume_slider.value()
        
        self.settings_manager.settings["tts_enabled_twitch"] = self.check_twitch.isChecked()
        self.settings_manager.settings["tts_enabled_tiktok"] = self.check_tiktok.isChecked()
        self.settings_manager.settings["tts_enabled_kick"] = self.check_kick.isChecked()
        
        self.settings_manager.settings["tts_voice_twitch"] = self.combo_twitch.currentData()
        self.settings_manager.settings["tts_voice_tiktok"] = self.combo_tiktok.currentData()
        self.settings_manager.settings["tts_voice_kick"] = self.combo_kick.currentData()
        
        current_lang_index = self.lang_combo.currentIndex()
        self.settings_manager.settings["language"] = self.lang_codes[current_lang_index] if current_lang_index < len(self.lang_codes) else "pt-br"
        
        self.settings_manager.settings["font_family"] = self.font_combo.currentText()
        self.settings_manager.settings["font_size"] = self.font_size_slider.value()
        self.settings_manager.settings["platform_colors"] = self.platform_colors
        
        self.settings_manager.settings["blacklist"] = self.tags
        
        # Salva hotkeys
        self.settings_manager.settings["hotkey_toggle_visibility"] = self.hotkey_toggle_field.text().strip() or "ctrl+shift+h"
        self.settings_manager.settings["hotkey_clear_chat"] = self.hotkey_clear_field.text().strip() or "ctrl+shift+c"
        
        self.settings_manager.save_settings()
        
        # Ao salvar, limpa toda a fila de voz antiga para aplicar as configurações apenas em novas mensagens
        if hasattr(self.main_window, "tts_manager"):
            self.main_window.tts_manager.clear_queue()
            
        self.accept()
