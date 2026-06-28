"""
AirPods Auto-Switch — Bluetooth Manager
Connects / disconnects a paired Bluetooth audio device by toggling
its PnP (Plug and Play) device entry via PowerShell.

Requires admin privileges (the app auto-elevates via main.py).
"""

import ctypes
from ctypes import wintypes
import logging
import os
import subprocess
import time

from settings_manager import settings

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────
BLUETOOTH_MAX_NAME_SIZE   = 248
ERROR_SUCCESS             = 0
INVALID_HANDLE_VALUE      = wintypes.HANDLE(-1).value

# ── C Structures (for device discovery only) ───────────────────────────

class BLUETOOTH_ADDRESS(ctypes.Union):
    _fields_ = [
        ("ullLong", ctypes.c_ulonglong),
        ("rgBytes", ctypes.c_ubyte * 6),
    ]

class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ("wYear",         ctypes.c_ushort),
        ("wMonth",        ctypes.c_ushort),
        ("wDayOfWeek",    ctypes.c_ushort),
        ("wDay",          ctypes.c_ushort),
        ("wHour",         ctypes.c_ushort),
        ("wMinute",       ctypes.c_ushort),
        ("wSecond",       ctypes.c_ushort),
        ("wMilliseconds", ctypes.c_ushort),
    ]

class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize",          ctypes.c_ulong),
        ("Address",         BLUETOOTH_ADDRESS),
        ("ulClassofDevice", ctypes.c_ulong),
        ("fConnected",      wintypes.BOOL),
        ("fRemembered",     wintypes.BOOL),
        ("fAuthenticated",  wintypes.BOOL),
        ("stLastSeen",      SYSTEMTIME),
        ("stLastUsed",      SYSTEMTIME),
        ("szName",          ctypes.c_wchar * BLUETOOTH_MAX_NAME_SIZE),
    ]

    def __init__(self):
        super().__init__()
        self.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_INFO)

class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
    _fields_ = [
        ("dwSize",              ctypes.c_ulong),
        ("fReturnAuthenticated", wintypes.BOOL),
        ("fReturnRemembered",    wintypes.BOOL),
        ("fReturnUnknown",       wintypes.BOOL),
        ("fReturnConnected",     wintypes.BOOL),
        ("fIssueInquiry",        wintypes.BOOL),
        ("cTimeoutMultiplier",   ctypes.c_ubyte),
        ("hRadio",               wintypes.HANDLE),
    ]

    def __init__(self):
        super().__init__()
        self.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_SEARCH_PARAMS)

class BLUETOOTH_FIND_RADIO_PARAMS(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong)]

    def __init__(self):
        super().__init__()
        self.dwSize = ctypes.sizeof(BLUETOOTH_FIND_RADIO_PARAMS)


# ── Load bthprops.cpl ─────────────────────────────────────────────────

try:
    _bth = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
except OSError:
    log.error("Could not load bthprops.cpl — is Bluetooth available?")
    _bth = None


def _bind_functions():
    if _bth is None:
        return

    _bth.BluetoothFindFirstRadio.restype  = wintypes.HANDLE
    _bth.BluetoothFindFirstRadio.argtypes = [
        ctypes.POINTER(BLUETOOTH_FIND_RADIO_PARAMS),
        ctypes.POINTER(wintypes.HANDLE),
    ]
    _bth.BluetoothFindRadioClose.restype  = wintypes.BOOL
    _bth.BluetoothFindRadioClose.argtypes = [wintypes.HANDLE]

    _bth.BluetoothFindFirstDevice.restype  = wintypes.HANDLE
    _bth.BluetoothFindFirstDevice.argtypes = [
        ctypes.POINTER(BLUETOOTH_DEVICE_SEARCH_PARAMS),
        ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
    ]
    _bth.BluetoothFindNextDevice.restype  = wintypes.BOOL
    _bth.BluetoothFindNextDevice.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
    ]
    _bth.BluetoothFindDeviceClose.restype  = wintypes.BOOL
    _bth.BluetoothFindDeviceClose.argtypes = [wintypes.HANDLE]


_bind_functions()


# ── BluetoothManager ──────────────────────────────────────────────────

class BluetoothManager:
    """Manages connection lifecycle for a paired Bluetooth audio device."""

    def __init__(self, device_name: str = None):
        self._device_name_override = device_name
        self._pnp_instance_id = None  # cached on first lookup

    @property
    def device_name(self):
        return self._device_name_override or settings.get("DEVICE_NAME", "AirPods")

    # ── Public API ────────────────────────────────────────────────────

    @staticmethod
    def _normalize(name):
        return (
            name.lower()
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201C", '"')
            .replace("\u201D", '"')
        )

    def is_available(self) -> bool:
        return _bth is not None

    def find_device(self) -> "BLUETOOTH_DEVICE_INFO | None":
        """Search paired/remembered devices for the target by name."""
        if not self.is_available():
            return None

        radio = self._get_radio()
        if radio is None:
            return None

        try:
            search_params = BLUETOOTH_DEVICE_SEARCH_PARAMS()
            search_params.fReturnAuthenticated = True
            search_params.fReturnRemembered    = True
            search_params.fReturnConnected     = True
            search_params.fReturnUnknown       = False
            search_params.fIssueInquiry        = False
            search_params.cTimeoutMultiplier   = 0
            search_params.hRadio               = radio

            device_info = BLUETOOTH_DEVICE_INFO()
            search_handle = _bth.BluetoothFindFirstDevice(
                ctypes.byref(search_params), ctypes.byref(device_info)
            )

            if search_handle == INVALID_HANDLE_VALUE:
                log.debug("No Bluetooth devices found.")
                return None

            try:
                while True:
                    name = device_info.szName
                    if self._normalize(name) == self._normalize(self.device_name):
                        log.info(f"Target device found: {name} (connected={bool(device_info.fConnected)})")
                        return device_info

                    device_info = BLUETOOTH_DEVICE_INFO()
                    if not _bth.BluetoothFindNextDevice(search_handle, ctypes.byref(device_info)):
                        break
            finally:
                _bth.BluetoothFindDeviceClose(search_handle)

        finally:
            ctypes.windll.kernel32.CloseHandle(radio)

        log.debug(f"Device '{self.device_name}' not found among paired devices.")
        return None

    def is_connected(self) -> bool:
        device = self.find_device()
        if device is None:
            return False
        return bool(device.fConnected)

    def _get_bttools_exe(self) -> str:
        """Get the persistent path to the BluetoothDevicePairing CLI tool."""
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        app_dir = os.path.join(local_app_data, "AirPodsAutoSwitch")
        return os.path.join(app_dir, "bttools", "BluetoothDevicePairing.exe")

    def connect(self) -> bool:
        """Connect AirPods using BluetoothDevicePairing CLI tool."""
        mac = self._get_mac_address()
        if not mac:
            log.warning("Cannot connect: Device MAC not found.")
            return False

        self._ensure_bttools()
        exe = self._get_bttools_exe()
        
        log.info(f"Connecting {self.device_name} (MAC: {mac})...")
        try:
            result = subprocess.run(
                [exe, "pair-by-mac", "--mac", mac, "--type", "Bluetooth"],
                capture_output=True, text=True, timeout=15
            )
            log.debug(f"Connect stdout: {result.stdout.strip()}")
            if result.returncode == 0:
                log.info(f"{self.device_name} connected.")
                return True
            else:
                log.error(f"Connect failed: {result.stderr.strip()}")
                return False
        except Exception as e:
            log.error(f"Connect exception: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect AirPods using BluetoothDevicePairing CLI tool."""
        mac = self._get_mac_address()
        if not mac:
            log.warning("Cannot disconnect: Device MAC not found.")
            return False

        self._ensure_bttools()
        exe = self._get_bttools_exe()
        
        log.info(f"Disconnecting {self.device_name} (MAC: {mac})...")
        try:
            result = subprocess.run(
                [exe, "disconnect-bluetooth-audio-device-by-mac", "--mac", mac, "--type", "Bluetooth"],
                capture_output=True, text=True, timeout=15
            )
            log.debug(f"Disconnect stdout: {result.stdout.strip()}")
            if result.returncode == 0:
                log.info(f"{self.device_name} disconnected.")
                return True
            else:
                log.error(f"Disconnect failed: {result.stderr.strip()}")
                return False
        except Exception as e:
            log.error(f"Disconnect exception: {e}")
            return False

    # ── Internal ──────────────────────────────────────────────────────

    def _get_mac_address(self) -> str:
        device = self.find_device()
        if not device:
            return None
        bytes_array = list(device.Address.rgBytes)
        hex_mac = ":".join(f"{b:02X}" for b in reversed(bytes_array))
        return hex_mac
        
    def _ensure_bttools(self):
        """Download the BluetoothDevicePairing CLI tool if it doesn't exist."""
        import urllib.request, zipfile
        exe_path = self._get_bttools_exe()
        bttools_dir = os.path.dirname(exe_path)
        
        if os.path.exists(exe_path):
            return
            
        log.info("Downloading BluetoothDevicePairing CLI tool...")
        os.makedirs(bttools_dir, exist_ok=True)
        zip_path = os.path.join(bttools_dir, "bt.zip")
        
        try:
            url = "https://github.com/PolarGoose/BluetoothDevicePairing/releases/download/v12.0/BluetoothDevicePairing.zip"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())
            
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(bttools_dir)
                
            os.remove(zip_path)
            log.info("BluetoothDevicePairing tool setup complete.")
        except Exception as e:
            log.error(f"Failed to setup bttools: {e}")

    def _get_radio(self) -> "wintypes.HANDLE | None":
        """Get a handle to the first Bluetooth radio."""
        params = BLUETOOTH_FIND_RADIO_PARAMS()
        radio_handle = wintypes.HANDLE()
        find_handle = _bth.BluetoothFindFirstRadio(
            ctypes.byref(params), ctypes.byref(radio_handle)
        )
        if find_handle == INVALID_HANDLE_VALUE:
            log.warning("No Bluetooth radio found.")
            return None
        _bth.BluetoothFindRadioClose(find_handle)
        return radio_handle.value
