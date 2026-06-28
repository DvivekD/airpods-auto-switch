"""
AirPods Auto-Switch — Audio Monitor
Detects whether Windows is currently outputting audio by checking ALL 
active render endpoints via WASAPI / pycaw. Supports App Blacklisting.
"""

import logging
import comtypes
from ctypes import cast, POINTER

from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CLSCTX_ALL

from settings_manager import settings

log = logging.getLogger(__name__)


class AudioMonitor:
    """Monitors active audio sessions for activity, applying app filtering."""

    def __init__(self):
        self._setup_done = False

    def get_peak_level(self) -> float:
        """
        Return the max peak audio level across non-blacklisted active sessions (0.0 – 1.0).
        Returns 0.0 on any error.
        """
        if not self._setup_done:
            comtypes.CoInitialize()
            self._setup_done = True

        max_peak = 0.0
        
        # Pull dynamic settings
        threshold = settings.get("AUDIO_THRESHOLD", 0.001)
        use_blacklist = settings.get("BLACKLIST_ENABLED", True)
        blacklist = settings.get("APP_BLACKLIST", [])

        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                try:
                    # Ignore System Sounds and other sessions without a valid process if needed
                    # "Idle" is sometimes reported for system things. 
                    proc_name = session.Process.name() if session.Process else None
                    
                    if use_blacklist and proc_name in blacklist:
                        continue # Skip blacklisted apps

                    # Try to read the peak meter for this specific session
                    try:
                        meter = cast(session._ctl, POINTER(IAudioMeterInformation))
                        val = meter.GetPeakValue()
                        if val > max_peak:
                            max_peak = val
                    except Exception:
                        pass
                    
                    # Fallback: if meter fails but session is Active
                    # 1 = AudioSessionStateActive
                    if max_peak < threshold and session._ctl.GetState() == 1:
                        max_peak = max(max_peak, 0.05) # Fake peak to trigger connect

                except Exception:
                    pass
        except Exception as e:
            log.error(f"Failed to enumerate audio sessions: {e}")
            return 0.0

        return max_peak

    def is_audio_playing(self) -> bool:
        """True if audio output exceeds the configured threshold."""
        level = self.get_peak_level()
        threshold = settings.get("AUDIO_THRESHOLD", 0.001)
        
        log.debug(f"Polled max peak level across devices: {level:.6f}")
        if level > threshold:
            log.debug(f"Audio playing (peak={level:.4f})")
            return True
        return False

    def cleanup(self):
        """Release COM resources."""
        self._setup_done = False
        try:
            comtypes.CoUninitialize()
        except Exception:
            pass
