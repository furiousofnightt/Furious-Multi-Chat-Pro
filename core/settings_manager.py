import json
import os
import sys

class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = self._resolve_settings_path(filename)
        self.settings = self.load_settings()

    def _resolve_settings_path(self, filename):
        candidates = []

        # 1) Diretório do script atual (execução normal)
        candidates.append(os.path.abspath(os.path.join(os.getcwd(), filename)))

        # 2) Diretório do projeto, mesmo quando o EXE roda de outra pasta
        project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        candidates.append(os.path.join(project_dir, filename))

        # 3) Diretório do executável empacotado / _MEIPASS
        try:
            if getattr(sys, '_MEIPASS', None):
                candidates.append(os.path.join(sys._MEIPASS, filename))
        except Exception:
            pass

        # 4) Diretório do executável original / script lançado
        try:
            run_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            candidates.append(os.path.join(run_dir, filename))
        except Exception:
            pass

        # 5) Diretório do arquivo em execução, se for um .exe
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidates.append(os.path.join(exe_dir, filename))
        except Exception:
            pass

        for path in candidates:
            if os.path.exists(path):
                return path

        return os.path.abspath(os.path.join(project_dir, filename))

    def load_settings(self):
        defaults = {
            "twitch": "",
            "tiktok": "",
            "kick": "",
            "language": "pt-br",
            "opacity": 0.85,
            "theme": "dark",
            "click_through": False,
            "blacklist": [],
            "font_family": "Segoe UI Variable Display",
            "font_size": 11,
            "platform_colors": {
                "twitch": "#9146FF",
                "tiktok": "#FF0050",
                "kick": "#53FC18",
                "system": "#333333"
            }
        }
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                
                # Descriptografa tiktok_session_id caso esteja criptografado com DPAPI
                session = loaded.get("tiktok_session_id", "")
                if session.startswith("DPAPI:"):
                    try:
                        import win32crypt
                        import base64
                        encrypted = base64.b64decode(session[6:].encode('utf-8'))
                        _, decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
                        loaded["tiktok_session_id"] = decrypted.decode('utf-8')
                    except Exception as e:
                        print(f"⚠️ Erro ao descriptografar sessão: {e}")
                        loaded["tiktok_session_id"] = ""

                defaults.update(loaded)
        return defaults

    def save_settings(self):
        to_save = self.settings.copy()
        
        # Criptografa tiktok_session_id com DPAPI antes de salvar
        session = to_save.get("tiktok_session_id", "")
        if session and not session.startswith("DPAPI:"):
            try:
                import win32crypt
                import base64
                encrypted = win32crypt.CryptProtectData(session.encode('utf-8'), "TikTokSession", None, None, None, 0)
                to_save["tiktok_session_id"] = "DPAPI:" + base64.b64encode(encrypted).decode('utf-8')
            except Exception as e:
                print(f"⚠️ Erro ao criptografar sessão: {e}")
        
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, indent=4)
