"""
AirPods Auto-Switch — System Tray App
Provides a tray icon with colour-coded status and a context menu
for snooze, manual connect/disconnect, and quit.
"""

import logging
import threading

import pystray
from PIL import Image, ImageDraw, ImageFont

from state_machine import State

log = logging.getLogger(__name__)

# ── Icon Colours ──────────────────────────────────────────────────────
STATE_COLORS = {
    State.IDLE:          ("#9CA3AF", "#6B7280"),  # Gray
    State.CONNECTING:    ("#60A5FA", "#3B82F6"),  # Blue
    State.CONNECTED:     ("#34D399", "#10B981"),  # Green
    State.COOLDOWN:      ("#FBBF24", "#F59E0B"),  # Amber
    State.DISCONNECTING: ("#F87171", "#EF4444"),  # Red
    State.SNOOZED:       ("#F87171", "#EF4444"),  # Red
    State.YIELDED:       ("#C084FC", "#A855F7"),  # Purple — handed to phone
}


def _make_icon(state: State, size: int = 64) -> Image.Image:
    """Generate a clean headphone icon with state-coloured accents."""
    fg, accent = STATE_COLORS.get(state, ("#9CA3AF", "#6B7280"))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 4

    # Headband arc (top half of a circle)
    draw.arc(
        [cx - r, cy - r, cx + r, cy + r],
        start=200, end=340,
        fill=fg, width=max(3, size // 16),
    )

    # Left ear cup
    cup_w, cup_h = size // 5, size // 3
    lx = cx - r + 2
    ly = cy
    draw.rounded_rectangle(
        [lx - cup_w // 2, ly - 2, lx + cup_w // 2, ly + cup_h],
        radius=cup_w // 3, fill=accent,
    )

    # Right ear cup
    rx = cx + r - 2
    ry = cy
    draw.rounded_rectangle(
        [rx - cup_w // 2, ry - 2, rx + cup_w // 2, ry + cup_h],
        radius=cup_w // 3, fill=accent,
    )

    # State dot (bottom-right corner)
    dot_r = size // 8
    draw.ellipse(
        [size - dot_r * 2 - 2, size - dot_r * 2 - 2, size - 2, size - 2],
        fill=accent,
    )

    return img


class TrayApp:
    """System tray interface for AirPods Auto-Switch."""

    def __init__(self, engine):
        """
        Args:
            engine: AutoSwitchEngine instance
        """
        self.engine = engine
        self.engine.on_state_change = self._on_state_change

        self._icon = pystray.Icon(
            name="AirPods Auto-Switch",
            icon=_make_icon(State.IDLE),
            title="AirPods Auto-Switch — Idle",
            menu=self._build_menu(),
        )

    # ── Public API ────────────────────────────────────────────────────

    def run(self):
        """Run the tray app (blocking). Call from main thread."""
        log.info("Tray app starting.")
        self._icon.run()

    def stop(self):
        """Stop the tray app."""
        self._icon.stop()

    # ── Menu ──────────────────────────────────────────────────────────

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: f"Status: {self.engine.state.value}",
                action=None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: "Resume" if self.engine.snoozed else "Snooze",
                self._on_snooze_toggle,
            ),
            pystray.MenuItem("Connect Now", self._on_connect),
            pystray.MenuItem("Disconnect Now", self._on_disconnect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._on_settings),
            pystray.MenuItem("Quit", self._on_quit),
        )

    # ── Callbacks ─────────────────────────────────────────────────────

    def _on_state_change(self, new_state: State):
        """Called by the engine when state changes. Update icon."""
        self._icon.icon = _make_icon(new_state)
        self._icon.title = f"AirPods Auto-Switch — {new_state.value}"
        try:
            self._icon.update_menu()
        except Exception:
            pass

    def _on_snooze_toggle(self, icon, item):
        self.engine.toggle_snooze()

    def _on_connect(self, icon, item):
        threading.Thread(target=self.engine.manual_connect, daemon=True).start()

    def _on_disconnect(self, icon, item):
        threading.Thread(target=self.engine.manual_disconnect, daemon=True).start()

    def _on_quit(self, icon, item):
        log.info("Quit requested.")
        self.engine.stop()
        icon.stop()

    def _on_settings(self, icon, item):
        log.info("Settings requested.")
        import subprocess, sys
        subprocess.Popen([sys.executable, "--settings"])
