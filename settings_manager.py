import os
import json

DEFAULT_SETTINGS = {
    "DEVICE_NAME": "rei’s AirPods Pro",
    "AUDIO_THRESHOLD": 0.001,
    "DISCONNECT_TIMEOUT": 2,
    "CONNECTION_RETRY_DELAY": 5,
    "BLACKLIST_ENABLED": True,
    "APP_BLACKLIST": ["explorer.exe", "ms-teams.exe"] # Examples of annoying pinging apps
}

SETTINGS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AirPodsAutoSwitch")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR, exist_ok=True)
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"Failed to load settings: {e}")
        else:
            self.save()

    def save(self):
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR, exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        # Always reload on get to ensure we have the latest settings from GUI
        self.load()
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

# Global instance
settings = SettingsManager()
