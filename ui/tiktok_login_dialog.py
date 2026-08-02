"""
Janela de login do TikTok via navegador embutido (PyQt6-WebEngine).
Abre o site oficial do TikTok para que o usuário faça login normalmente.
Assim que o cookie 'sessionid' é detectado, ele é salvo e a janela fecha.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
from utils.resource_path import resource_path
import os


TIKTOK_LOGIN_URL = "https://www.tiktok.com/login"

class TikTokLoginDialog(QDialog):
    """
    Janela modal com mini-navegador Chrome embutido apontando para o login do TikTok.
    Emite o sinal 'login_success' com o sessionid quando o usuário logar.
    """
    # Emite (sessionid: str)
    login_success = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login TikTok — Furious Multi Chat")
        self.setMinimumSize(520, 680)
        self.resize(520, 680)
        self.setModal(True)

        # Ícone da janela
        icon_path = resource_path("assets/icone.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog { background-color: #111; color: white; }
            QLabel { color: #aaa; font-size: 12px; }
            QPushButton {
                background-color: #333; color: white;
                border: none; padding: 7px 14px; border-radius: 5px; font-size: 12px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton#cancel_btn { color: #ff6666; border: 1px solid #ff6666; }
            QPushButton#cancel_btn:hover { background-color: #ff6666; color: white; }
            QProgressBar {
                background-color: #222; border: none; border-radius: 2px; height: 3px;
            }
            QProgressBar::chunk { background-color: #fe2c55; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        # Cabeçalho
        header = QHBoxLayout()
        header.setContentsMargins(12, 10, 12, 6)
        title_lbl = QLabel("Faca login no TikTok para ativar lives +18")
        title_lbl.setStyleSheet("color: #eee; font-weight: bold; font-size: 13px;")
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(cancel_btn)
        layout.addLayout(header)

        # Barra de progresso de carregamento de página
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        layout.addWidget(self.progress)

        # O mini-navegador Chrome embutido com perfil isolado
        self.profile = QWebEngineProfile("tiktok_login_session", self)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )

        self.view = QWebEngineView(self.profile, self)
        layout.addWidget(self.view, 1)

        # Status bar inferior
        status_row = QHBoxLayout()
        status_row.setContentsMargins(12, 6, 12, 0)
        self.status_lbl = QLabel("Aguardando login...")
        self.status_lbl.setStyleSheet("color: #666; font-size: 10px;")
        status_row.addWidget(self.status_lbl)
        layout.addLayout(status_row)

        # Conectar sinais
        self.view.loadProgress.connect(self.progress.setValue)
        self.view.loadFinished.connect(self._on_load_finished)

        # Monitorar cookies em tempo real
        self.profile.cookieStore().cookieAdded.connect(self._on_cookie_added)

        # Navegar para o login
        self.view.setUrl(QUrl(TIKTOK_LOGIN_URL))

    def _on_cookie_added(self, cookie):
        """Chamado sempre que um cookie novo é definido no mini-navegador."""
        name = cookie.name().data().decode("utf-8", errors="ignore")
        domain = cookie.domain()
        if name == "sessionid" and "tiktok.com" in domain:
            value = cookie.value().data().decode("utf-8", errors="ignore")
            if value:
                self.status_lbl.setText("Login detectado! Salvando...")
                self.status_lbl.setStyleSheet("color: #00cc66; font-weight: bold; font-size: 10px;")
                # Fechar quase que imediatamente após sucesso!
                QTimer.singleShot(800, lambda: self._finish_login(value))

    def _finish_login(self, session_id):
        self.login_success.emit(session_id)
        self.accept()

    def _on_load_finished(self, ok):
        url = self.view.url().toString()
        if ok:
            if "/login" in url or "passport" in url:
                self.status_lbl.setText("Faça o login normalmente — detectaremos automaticamente.")
                self.status_lbl.setStyleSheet("color: #888; font-size: 10px;")
            elif "tiktok.com" in url and "/login" not in url:
                self.status_lbl.setText("Carregando sessao...")
                self.status_lbl.setStyleSheet("color: #888; font-size: 10px;")
