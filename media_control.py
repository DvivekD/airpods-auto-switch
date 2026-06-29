"""
AirPods Auto-Switch — Media Control
Send media key events to Windows to pause/play audio globally.
"""

import ctypes
import logging

log = logging.getLogger(__name__)

VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def send_media_pause():
    """Send a Media Play/Pause key press to pause whatever is currently playing."""
    try:
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)
        log.info("Sent media PAUSE key event.")
    except Exception as e:
        log.error(f"Failed to send media pause key: {e}")
