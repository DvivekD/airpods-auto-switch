"""
AirPods Auto-Switch — Audio Monitor
Detects whether Windows is currently outputting audio by checking ALL 
active render endpoints via WASAPI / pycaw.
"""

import logging
import comtypes
from ctypes import cast, POINTER

from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from pycaw.constants import EDataFlow
from comtypes import CLSCTX_ALL

from config import AUDIO_THRESHOLD

log = logging.getLogger(__name__)


class AudioMonitor:
    """Monitors all active audio output devices for activity."""

    def __init__(self, threshold: float = AUDIO_THRESHOLD):
        self.threshold = threshold
        self._setup_done = False
        self._meters = []

    def _reset(self):
        log.debug("Resetting audio meters...")
        self._meters.clear()
        self._setup_done = False

    def get_peak_level(self) -> float:
        """
        Return the max peak audio level across all active output devices (0.0 – 1.0).
        Returns 0.0 on any error.
        """
        if not self._setup_done:
            # Need to initialize COM on this thread
            comtypes.CoInitialize()
            
            enumerator = AudioUtilities.GetDeviceEnumerator()
            # 1 = DEVICE_STATE_ACTIVE
            try:
                collection = enumerator.EnumAudioEndpoints(EDataFlow.eRender.value, 1)
                count = collection.GetCount()
                for i in range(count):
                    dev = collection.Item(i)
                    try:
                        interface = dev.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                        meter = cast(interface, POINTER(IAudioMeterInformation))
                        self._meters.append(meter)
                    except Exception:
                        pass
                self._setup_done = True
            except Exception as e:
                log.error(f"Failed to enumerate audio devices: {e}")
                return 0.0

        max_peak = 0.0
        dead_meters = []
        for meter in self._meters:
            try:
                val = meter.GetPeakValue()
                if val > max_peak:
                    max_peak = val
            except Exception:
                dead_meters.append(meter)
                
        if dead_meters:
            for m in dead_meters:
                self._meters.remove(m)
            self._setup_done = False

        # Fallback for virtual devices (like GG Sonar) that might not expose meters:
        # Check if any audio session is active.
        if max_peak == 0.0:
            try:
                sessions = AudioUtilities.GetAllSessions()
                for session in sessions:
                    try:
                        # AudioSessionStateActive = 1
                        if session._ctl.GetState() == 1:
                            return 0.05 # Fake peak above threshold to trigger connect
                    except Exception:
                        pass
            except Exception:
                pass

        return max_peak

    def is_audio_playing(self) -> bool:
        """True if audio output exceeds the configured threshold."""
        level = self.get_peak_level()
        log.debug(f"Polled max peak level across devices: {level:.6f}")
        if level > self.threshold:
            log.debug(f"Audio playing (peak={level:.4f})")
            return True
        return False

    def cleanup(self):
        """Release COM resources."""
        self._reset()
        try:
            comtypes.CoUninitialize()
        except Exception:
            pass
