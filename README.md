# AirPods Auto-Switch for Windows

A seamless system tray utility that automatically connects your AirPods to your Windows PC when audio starts playing, and gracefully disconnects them after a period of silence so they can reconnect to your iPhone/iPad.

## Features

- **Seamless Auto-Switching:** Monitors Windows audio sessions and connects to your paired AirPods automatically when music, videos, or games start playing.
- **Smart Cooldown:** Automatically releases the Bluetooth connection back to your Apple devices after 5 seconds of silence (configurable).
- **Core Audio Integration:** Uses native `IAudioSessionManager2` APIs to detect audio output across all devices and virtual endpoints (compatible with GG Sonar, Voicemeeter, etc.).
- **Reliable Bluetooth Routing:** Uses undocumented Windows Core Audio `IPolicyConfig` APIs via `BluetoothDevicePairing.exe` to guarantee the A2DP and Hands-Free audio profiles are properly routed without requiring Administrator privileges.
- **System Tray Icon:** Lightweight background app with a clean UI indicating your connection status (Idle, Connecting, Connected, Cooldown).

## Installation

### Option 1: Standalone Executable (Recommended)
1. Download the latest `AirPodsAutoSwitch.exe` from the Releases page.
2. Double-click it to run. It will silently appear in your system tray.
3. (Optional) Place the `.exe` (or a shortcut to it) in your `shell:startup` folder to have it launch automatically when Windows boots.

### Option 2: Run from Source
1. Clone this repository.
2. Install dependencies:
   ```cmd
   pip install pystray pillow pycaw comtypes
   ```
3. Run the script:
   ```cmd
   python main.py
   ```

*(Note: On the first run, the app will automatically download the required `BluetoothDevicePairing.exe` CLI tool into your `%LOCALAPPDATA%\AirPodsAutoSwitch` folder.)*

## Configuration

You can tweak settings directly inside `config.py` (if running from source):

- `DEVICE_NAME`: The exact name of your AirPods as they appear in Windows Bluetooth Settings (e.g. `"John's AirPods Pro"`).
- `DISCONNECT_TIMEOUT`: Number of seconds of silence before releasing the AirPods back to your other devices (default is 5).
- `AUDIO_THRESHOLD`: The minimum peak volume level (0.0 to 1.0) to register as "playing".

## How It Works

1. **Audio Monitor (`audio_monitor.py`)**: Uses the `pycaw` library to hook into the Windows Core Audio APIs and polls all active audio sessions across every device endpoint, detecting peak audio meters.
2. **State Machine (`state_machine.py`)**: Processes the audio peaks and manages transitions (Idle -> Connecting -> Connected -> Cooldown -> Idle).
3. **Bluetooth Manager (`bluetooth_manager.py`)**: Uses a CTypes wrapper to query `bthprops.cpl` and grab the MAC address of your AirPods. It then delegates the heavy lifting of audio profile routing to [PolarGoose's BluetoothDevicePairing](https://github.com/PolarGoose/BluetoothDevicePairing) tool.

## Requirements
- Windows 10 or Windows 11
- AirPods must be manually paired to the Windows PC at least once prior to use.
