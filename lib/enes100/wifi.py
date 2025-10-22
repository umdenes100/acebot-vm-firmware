# /lib/enes100/wifi.py
# MicroPython helper to connect to SSID 'umd-iot' using a per-device password
# looked up by this device's Wi-Fi MAC from a simple text file.
import network
import time
import sys
# MicroPython 'os' is usually named 'uos'
try:
    import uos as os
except ImportError:
    import os  # fallback if port exposes 'os'
def _normalize_mac(s):
    """
    Normalize MAC string: remove separators, uppercase.
    Accepts bytes (from WLAN.config('mac')) or str.
    Returns 12-char uppercase hex without separators.
    """
    if isinstance(s, bytes):
        return ''.join('{:02X}'.format(b) for b in s)
    s = s.strip()
    for sep in (':', '-', '.'):
        s = s.replace(sep, '')
    return s.upper()
def _join(a, b):
    if not a:
        return b
    if a.endswith('/'):
        return a + b
    return a + '/' + b
def _dirname_of_this_module():
    # Many MicroPython builds define __file__ for modules in /lib.
    # If it's missing, return None and we'll skip "module dir" checks.
    try:
        here = __file__
        # Normalize potential backslashes (some ports)
        here = here.replace('\\', '/')
        # Strip filename
        idx = here.rfind('/')
        return here[:idx] if idx >= 0 else None
    except Exception:
        return None
def _file_exists(path):
    try:
        s = os.stat(path)
        return True if s else False
    except Exception:
        return False
def _find_password_file(preferred=None):
    """
    Return the first existing path among common candidates.
    """
    candidates = []
    # 1) If caller passed an explicit path:
    if preferred:
        candidates.append(preferred)
    # Accept both spellings
    base_names = []
    # If preferred is just a filename, try both variants
    if (not preferred) or ('/' not in preferred):
        base_names.extend(['wifi_secretes.txt', 'wifi_secrets.txt'])
    # 2) Current working directory
    try:
        cwd = os.getcwd()
    except Exception:
        cwd = ''
    for name in base_names:
        candidates.append(_join(cwd, name))
    # 3) Same directory as this module (typically /lib/enes100)
    module_dir = _dirname_of_this_module()
    if module_dir:
        for name in base_names:
            candidates.append(_join(module_dir, name))
    # 4) Filesystem root
    for name in base_names:
        candidates.append('/' + name)
    # Return the first one that exists
    for path in candidates:
        if path and _file_exists(path):
            return path, candidates
    # None found
    return None, candidates
def _load_password_map(path_or_none):
    """
    Open the secrets file and return {NORMALIZED_MAC: password}.
    Tries multiple candidate locations if a relative name was given or None.
    Raises RuntimeError with details if not found.
    """
    real_path, tried = _find_password_file(path_or_none)
    if not real_path:
        msg = "Password file not found. Tried:\n" + "\n".join(" - " + p for p in tried)
        raise RuntimeError(msg)
    pwmap = {}
    try:
        with open(real_path, 'r') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(None, 1)  # split on first any-whitespace (space/tab)
                if len(parts) != 2:
                    continue
                mac_str, password = parts[0], parts[1]
                pwmap[_normalize_mac(mac_str)] = password.strip()
    except OSError as e:
        raise RuntimeError("Failed to read password file '{}': {}".format(real_path, e))
    if not pwmap:
        raise RuntimeError("Password file '{}' is empty or contains no valid entries.".format(real_path))
    return pwmap
def _connect(ssid, password, timeout_s=20):
    """
    Connect to Wi-Fi with timeout. Returns True if connected, False otherwise.
    """
    wlan = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    # Ensure AP is off and STA is on
    try:
        ap.active(False)
    except Exception:
        pass
    if not wlan.active():
        wlan.active(True)
    # If already connected to the target SSID, short-circuit
    try:
        if wlan.isconnected():
            try:
                current = wlan.config('essid')
            except Exception:
                current = None
            if (current and current == ssid):
                return True
    except Exception:
        pass
    # Start connection
    wlan.connect(ssid, password)
    start = time.ticks_ms()
    while True:
        if wlan.isconnected():
            return True
        if time.ticks_diff(time.ticks_ms(), start) > int(timeout_s * 1000):
            return False
        time.sleep_ms(200)
def _fmt_mac(mac_bytes):
    return ':'.join('{:02x}'.format(b) for b in mac_bytes)
def connect(password_file=None, ssid='umd-iot', timeout_s=20, debug=False):
    """
    Look up this device's MAC in a secrets file and connect to `ssid`.
    Returns True on success, else raises RuntimeError.
    """
    # Ensure AP is off
    try:
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
    except Exception:
        pass  # Some ports may not have AP_IF
    wlan = network.WLAN(network.STA_IF)
    # Set a specific station MAC if desired (uses NEW_MAC constant)
    set_station_mac(wlan, NEW_MAC)
    # Fully cycle STA to avoid stale state
    if wlan.active():
        wlan.active(False)
        time.sleep_ms(150)
    wlan.active(True)
    # (Optional) DEBUG: this block can be removed if NEW_MAC is authoritative
    TARGET_MAC = b'\xbc\xdd\xc2\x24\xa8\x6c'
    try:
        if TARGET_MAC is not None:
            if not isinstance(TARGET_MAC, (bytes, bytearray)) or len(TARGET_MAC) != 6:
                raise ValueError("TARGET_MAC must be 6-byte bytes.")
            wlan.config(mac=TARGET_MAC)
            if wlan.config('mac') != TARGET_MAC and debug:
                print("Warning: MAC set did not take; firmware may not allow changing MAC.")
    except OSError as e:
        if debug:
            print("MAC set skipped:", e)
    mac_bytes = wlan.config('mac')  # bytes
    my_mac_norm = _normalize_mac(mac_bytes)  # <<< IMPORTANT FIX
    if debug:
        print("Device MAC:", _fmt_mac(mac_bytes))
    pwmap = _load_password_map(password_file)
    password = pwmap.get(my_mac_norm)
    if password is None:
        raise RuntimeError("No password found for MAC {} in the secrets file."
                           .format(_fmt_mac(mac_bytes)))
    # Fresh connect
    try:
        wlan.disconnect()
    except Exception:
        pass
    wlan.connect(ssid, password)
    # Wait for connection or timeout
    t0 = time.ticks_ms()
    while not wlan.isconnected():
        status = wlan.status()
        if status in (-1, -2, -3):
            break
        if time.ticks_diff(time.ticks_ms(), t0) > int(timeout_s * 1000):
            break
        time.sleep_ms(200)
    if not wlan.isconnected():
        raise RuntimeError("Failed to connect to '{}' within {}s (status: {})."
                           .format(ssid, timeout_s, wlan.status()))
    if debug:
        print("Connected:", wlan.ifconfig())
    return True
NEW_MAC_STR = "bc:dd:c2:24:a8:6c"
NEW_MAC = bytes(int(x, 16) for x in NEW_MAC_STR.split(":"))
STEP_DELAY = 5
def wait_delay(msg=""):
    if msg: print(msg)
    time.sleep(STEP_DELAY)
# Simple REPL test
if __name__ == '__main__':
    try:
        connect(debug=True)  # will auto-search for the secrets file
    except Exception as e:
        sys.print_exception(e)
def set_station_mac(wlan, mac_bytes):
    print("[1/3] Setting station MAC to", NEW_MAC_STR)
    try:
        wlan.active(False); time.sleep(0.2)
        wlan.active(True);  time.sleep(0.2)
        wlan.config(mac=mac_bytes)
        cur = wlan.config("mac")
        if isinstance(cur, (bytes, bytearray)):
            print("    MAC readback:", ":".join("{:02x}".format(b) for b in cur))
    except Exception as e:
        print("    Warning: unable to set MAC:", e)
    wait_delay(f"    Waiting {STEP_DELAY}s...")