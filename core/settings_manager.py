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
            "youtube": "",
            "language": "pt-br",
            "opacity": 0.85,
            "bg_opacity": 0.75,
            "text_opacity": 1.0,
            "theme": "dark",
            "click_through": False,
            "blacklist": [],
            "font_family": "Segoe UI Variable Display",
            "font_size": 11,
            "platform_colors": {
                "twitch": "#9146FF",
                "tiktok": "#FF0050",
                "kick": "#53FC18",
                "youtube": "#FF0000",
                "system": "#333333"
            }
        }
        # Tentar carregar do arquivo principal; se corrompido, tenta o backup (.bak)
        loaded = None
        for path_to_try in (self.filename, f"{self.filename}.bak"):
            if os.path.exists(path_to_try):
                try:
                    with open(path_to_try, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                    if loaded:
                        break
                except Exception as e:
                    print(f"⚠️ Falha ao ler {path_to_try}: {e}")

        if loaded:
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

            # Compatibilidade retroativa com bg_opacity e text_opacity
            if "bg_opacity" not in loaded and "opacity" in loaded:
                loaded["bg_opacity"] = loaded["opacity"]
            if "text_opacity" not in loaded:
                loaded["text_opacity"] = 1.0

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

        # 1. Backup de segurança do arquivo anterior
        bak_file = f"{self.filename}.bak"
        if os.path.exists(self.filename):
            try:
                import shutil
                shutil.copy2(self.filename, bak_file)
            except Exception:
                pass

        # 2. Escrita atômica (grava em .tmp e renomeia) para evitar corrupção por queda de energia
        tmp_file = f"{self.filename}.tmp"
        try:
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(to_save, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, self.filename)
        except Exception as e:
            print(f"⚠️ Erro ao salvar configurações atomicamente: {e}")
            # Fallback direto caso o replace falhe
            try:
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump(to_save, f, indent=4)
            except Exception:
                pass
