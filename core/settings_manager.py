import json
import os

class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.settings = self.load_settings()

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
                defaults.update(loaded)
        return defaults

    def save_settings(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4)
