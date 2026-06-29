import os
import json
import random
import string


def _generate_topic():
    """Generate a random topic name for ntfy.sh handoff."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"airpods-switch-{suffix}"


DEFAULT_SETTINGS = {
    "DEVICE_NAME": "rei\u2019s AirPods Pro",
    "AUDIO_THRESHOLD": 0.001,
    "DISCONNECT_ON_SILENCE": False,
    "DISCONNECT_TIMEOUT": 2,
    "CONNECTION_RETRY_DELAY": 5,
    "BLACKLIST_ENABLED": True,
    "APP_BLACKLIST": ["explorer.exe", "ms-teams.exe"],
    "HANDOFF_ENABLED": True,
    "HANDOFF_TOPIC": "",  # Generated once on first run, then persisted
}

SETTINGS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AirPodsAutoSwitch")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()
        self._ensure_handoff_topic()

    def _ensure_handoff_topic(self):
        """Generate a stable handoff topic on first run and persist it."""
        if not self.settings.get("HANDOFF_TOPIC"):
            self.settings["HANDOFF_TOPIC"] = _generate_topic()
            self.save()

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
