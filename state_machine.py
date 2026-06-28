"""
AirPods Auto-Switch — State Machine
Core logic: monitors audio, manages Bluetooth connection lifecycle,
handles cooldown timers, and snooze state.
"""

import enum
import time
import threading
import logging

from audio_monitor import AudioMonitor
from bluetooth_manager import BluetoothManager
from settings_manager import settings
from config import AUDIO_POLL_INTERVAL

log = logging.getLogger(__name__)


class State(enum.Enum):
    IDLE          = "Idle"
    CONNECTING    = "Connecting…"
    CONNECTED     = "Connected"
    COOLDOWN      = "Cooldown"
    DISCONNECTING = "Disconnecting…"
    SNOOZED       = "Snoozed"


class AutoSwitchEngine:
    """
    Runs a background loop that:
      1. Polls audio output levels every few seconds
      2. Connects AirPods when audio is detected
      3. Disconnects after a silence timeout
      4. Supports snooze to pause auto-switching
    """

    def __init__(
        self,
        audio_monitor: AudioMonitor,
        bt_manager: BluetoothManager,
        on_state_change=None,
    ):
        self.audio = audio_monitor
        self.bt = bt_manager
        self.on_state_change = on_state_change

        self._state = State.IDLE
        self._snoozed = False
        self._cooldown_start = None
        self._last_connect_attempt: float = 0

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    # ── Properties ────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    @state.setter
    def state(self, new: State):
        with self._lock:
            old = self._state
            self._state = new
        if old != new:
            log.info(f"State: {old.value} → {new.value}")
            if self.on_state_change:
                try:
                    self.on_state_change(new)
                except Exception as exc:
                    log.debug(f"State change callback error: {exc}")

    @property
    def snoozed(self) -> bool:
        with self._lock:
            return self._snoozed

    # ── Public API ────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AutoSwitchEngine")
        self._thread.start()
        log.info("Engine started.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        log.info("Engine stopped.")

    def snooze(self):
        with self._lock:
            self._snoozed = True
        log.info("Snoozed — auto-switching paused.")
        if self.state in (State.CONNECTED, State.COOLDOWN, State.CONNECTING):
            self._do_disconnect()
        self.state = State.SNOOZED

    def unsnooze(self):
        with self._lock:
            self._snoozed = False
        log.info("Unsnooze — auto-switching resumed.")
        self.state = State.IDLE

    def toggle_snooze(self):
        if self.snoozed:
            self.unsnooze()
        else:
            self.snooze()

    def manual_connect(self):
        if self.snoozed:
            return
        self._do_connect()

    def manual_disconnect(self):
        self._do_disconnect()
        self.state = State.IDLE

    # ── Main Loop ─────────────────────────────────────────────────────

    def _loop(self):
        """Background thread: poll audio, manage state transitions."""
        _last_state_log = 0

        while self._running:
            try:
                if self.snoozed:
                    time.sleep(AUDIO_POLL_INTERVAL)
                    continue

                current = self.state
                audio_playing = self.audio.is_audio_playing()

                # Log current state every ~30 seconds for debugging
                now = time.monotonic()
                if now - _last_state_log > 30:
                    remaining = ""
                    if current == State.COOLDOWN and self._cooldown_start:
                        elapsed = now - self._cooldown_start
                        remaining = f" ({settings.get('DISCONNECT_TIMEOUT', 2) - elapsed:.0f}s remaining)"
                    log.info(f"[tick] state={current.value}, audio={audio_playing}{remaining}")
                    _last_state_log = now

                if current == State.IDLE:
                    if audio_playing:
                        self._do_connect()

                elif current == State.CONNECTED:
                    if not audio_playing:
                        self._start_cooldown()

                elif current == State.COOLDOWN:
                    if audio_playing:
                        log.info("Audio resumed during cooldown — staying connected.")
                        self._cooldown_start = None
                        self.state = State.CONNECTED
                    elif self._cooldown_expired():
                        self._do_disconnect()
                        self.state = State.IDLE

            except Exception as exc:
                log.error(f"Loop error: {exc}", exc_info=True)

            time.sleep(AUDIO_POLL_INTERVAL)

    # ── State Transitions ─────────────────────────────────────────────

    def _do_connect(self):
        """Attempt to connect AirPods."""
        now = time.monotonic()
        if now - self._last_connect_attempt < settings.get('CONNECTION_RETRY_DELAY', 5):
            return

        self._last_connect_attempt = now
        self.state = State.CONNECTING

        if self.bt.connect():
            # Reset audio meters — new endpoints appeared after PnP toggle
            self.audio._reset()
            self.state = State.CONNECTED
        else:
            log.info("Connection failed — will retry on next audio cycle.")
            self.state = State.IDLE

    def _do_disconnect(self):
        """Disconnect AirPods."""
        self.state = State.DISCONNECTING
        self.bt.disconnect()
        self._cooldown_start = None
        # Reset audio meters — endpoints changed after PnP disable
        self.audio._reset()

    def _start_cooldown(self):
        self._cooldown_start = time.monotonic()
        self.state = State.COOLDOWN
        log.info(f"Audio stopped — cooldown started ({settings.get('DISCONNECT_TIMEOUT', 2)}s).")

    def _cooldown_expired(self) -> bool:
        if self._cooldown_start is None:
            return False
        return (time.monotonic() - self._cooldown_start) >= settings.get('DISCONNECT_TIMEOUT', 2)
