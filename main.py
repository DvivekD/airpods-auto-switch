"""
AirPods Auto-Switch
───────────────────
Automatically connects your AirPods to Windows when audio plays,
and releases them back to iPhone/iPad after silence.

Usage:  python main.py
"""

import sys
import os
import ctypes
import logging

from config import LOG_LEVEL


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    if "--settings" in sys.argv:
        import gui
        gui.open_settings_window()
        sys.exit(0)

    setup_logging()
    log = logging.getLogger("main")

    log.info("=" * 50)
    log.info("  AirPods Auto-Switch starting")
    log.info("=" * 50)

    from audio_monitor import AudioMonitor
    from bluetooth_manager import BluetoothManager
    from state_machine import AutoSwitchEngine
    from tray_app import TrayApp

    # ── Initialise components ─────────────────────────────────────────
    bt = BluetoothManager()

    if not bt.is_available():
        log.error("Bluetooth is not available. Exiting.")
        sys.exit(1)

    device = bt.find_device()
    if device:
        log.info(f"Found target device: {device.szName}")
    else:
        log.warning(
            f"Target device not found in paired list. "
            f"Will keep looking during runtime."
        )

    audio = AudioMonitor()
    engine = AutoSwitchEngine(audio_monitor=audio, bt_manager=bt)
    tray = TrayApp(engine)

    # ── Start ─────────────────────────────────────────────────────────
    engine.start()

    try:
        tray.run()  # Blocking — runs the Windows message loop
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        audio.cleanup()
        log.info("Goodbye.")


if __name__ == "__main__":
    main()
