"""
AirPods Auto-Switch — Configuration
All tuneable constants in one place.
"""

# ── Bluetooth Device ──
DEVICE_NAME = "rei\u2019s AirPods Pro"  # Note: uses Unicode right quote (U+2019)

# ── Audio Detection ──
AUDIO_POLL_INTERVAL = 3        # seconds between audio level checks
AUDIO_THRESHOLD = 0.001        # minimum peak level to count as "audio playing"

# ── Timing ──
DISCONNECT_TIMEOUT = 2         # seconds of silence before releasing AirPods
CONNECTION_RETRY_DELAY = 5     # seconds to wait after a failed connection attempt

# ── Logging ──
LOG_LEVEL = "DEBUG"  # DEBUG for verbose output
