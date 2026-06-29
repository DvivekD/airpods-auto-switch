import customtkinter as ctk
from settings_manager import settings

# Global reference to avoid opening multiple instances
_settings_window = None

class SettingsGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AirPods Auto-Switch Settings")
        self.geometry("400x720")
        self.resizable(False, False)
        
        # Appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Load values
        self.device_name_var = ctk.StringVar(value=settings.get("DEVICE_NAME", ""))
        self.timeout_var = ctk.IntVar(value=settings.get("DISCONNECT_TIMEOUT", 2))
        self.blacklist_enabled_var = ctk.BooleanVar(value=settings.get("BLACKLIST_ENABLED", True))
        self.handoff_enabled_var = ctk.BooleanVar(value=settings.get("HANDOFF_ENABLED", True))
        
        # Join blacklist array into comma separated string for easy editing
        blacklist = settings.get("APP_BLACKLIST", [])
        self.blacklist_var = ctk.StringVar(value=", ".join(blacklist))

        self.build_ui()

    def build_ui(self):
        # ── Device Name ──
        label_dev = ctk.CTkLabel(self, text="AirPods Device Name", font=ctk.CTkFont(size=14, weight="bold"))
        label_dev.pack(pady=(20, 5), padx=20, anchor="w")
        
        entry_dev = ctk.CTkEntry(self, textvariable=self.device_name_var, width=360)
        entry_dev.pack(pady=0, padx=20)
        
        desc_dev = ctk.CTkLabel(self, text="The exact name as it appears in Windows Bluetooth.", text_color="gray", font=ctk.CTkFont(size=11))
        desc_dev.pack(pady=(0, 20), padx=20, anchor="w")

        # ── Disconnect Timeout (Slider) ──
        label_time = ctk.CTkLabel(self, text=f"Disconnect Cooldown: {self.timeout_var.get()}s", font=ctk.CTkFont(size=14, weight="bold"))
        label_time.pack(pady=(10, 5), padx=20, anchor="w")
        
        slider_time = ctk.CTkSlider(self, from_=0, to=30, variable=self.timeout_var, number_of_steps=30, width=360, command=lambda v: label_time.configure(text=f"Disconnect Cooldown: {int(v)}s"))
        slider_time.pack(pady=0, padx=20)
        
        desc_time = ctk.CTkLabel(self, text="Seconds of silence before disconnecting.", text_color="gray", font=ctk.CTkFont(size=11))
        desc_time.pack(pady=(0, 20), padx=20, anchor="w")

        # ── App Blacklist ──
        label_bl = ctk.CTkLabel(self, text="App Blacklist", font=ctk.CTkFont(size=14, weight="bold"))
        label_bl.pack(pady=(10, 5), padx=20, anchor="w")
        
        switch_bl = ctk.CTkSwitch(self, text="Enable Blacklist (Ignore these apps)", variable=self.blacklist_enabled_var)
        switch_bl.pack(pady=5, padx=20, anchor="w")
        
        entry_bl = ctk.CTkEntry(self, textvariable=self.blacklist_var, width=360)
        entry_bl.pack(pady=0, padx=20)
        
        desc_bl = ctk.CTkLabel(self, text="Comma-separated. e.g. explorer.exe, ms-teams.exe", text_color="gray", font=ctk.CTkFont(size=11))
        desc_bl.pack(pady=(0, 20), padx=20, anchor="w")

        # ── iPhone Handoff ──
        label_ho = ctk.CTkLabel(self, text="iPhone Handoff", font=ctk.CTkFont(size=14, weight="bold"))
        label_ho.pack(pady=(10, 5), padx=20, anchor="w")
        
        switch_ho = ctk.CTkSwitch(self, text="Enable iPhone Handoff (via ntfy.sh)", variable=self.handoff_enabled_var)
        switch_ho.pack(pady=5, padx=20, anchor="w")

        # Show the handoff URL
        topic = settings.get("HANDOFF_TOPIC", "")
        handoff_url = f"https://ntfy.sh/{topic}" if topic else "Not configured"
        
        desc_ho = ctk.CTkLabel(self, text="iPhone Shortcut URL (copy this):", text_color="gray", font=ctk.CTkFont(size=11))
        desc_ho.pack(pady=(5, 2), padx=20, anchor="w")
        
        url_entry = ctk.CTkEntry(self, width=360)
        url_entry.pack(pady=0, padx=20)
        url_entry.insert(0, handoff_url)
        url_entry.configure(state="readonly")

        desc_ho2 = ctk.CTkLabel(
            self, 
            text="Create an iPhone Shortcut: When I open [app]\n→ Get Contents of URL (POST to above URL)\n→ Toggle off 'Ask Before Running'",
            text_color="gray", 
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        desc_ho2.pack(pady=(5, 20), padx=20, anchor="w")

        # ── Save Button ──
        btn_save = ctk.CTkButton(self, text="Save Settings", command=self.save_settings, width=200, height=40)
        btn_save.pack(pady=20)
        
        # Override close behavior
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def save_settings(self):
        settings.set("DEVICE_NAME", self.device_name_var.get())
        settings.set("DISCONNECT_TIMEOUT", int(self.timeout_var.get()))
        settings.set("BLACKLIST_ENABLED", self.blacklist_enabled_var.get())
        settings.set("HANDOFF_ENABLED", self.handoff_enabled_var.get())
        
        # Parse comma-separated list
        raw_list = self.blacklist_var.get().split(",")
        clean_list = [app.strip() for app in raw_list if app.strip()]
        settings.set("APP_BLACKLIST", clean_list)
        
        self.on_close()

    def on_close(self):
        global _settings_window
        self.destroy()
        _settings_window = None


def open_settings_window():
    global _settings_window
    if _settings_window is None:
        _settings_window = SettingsGUI()
        _settings_window.mainloop()
    else:
        _settings_window.focus()
