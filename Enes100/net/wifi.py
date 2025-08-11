import time
from ..utils import log


def ensure_wifi(ssid, password, *, mac_spoof=None, timeout_s=12, retries=3):
    """Connect to Wi‑Fi STA, with optional MAC spoof and simple retries.
    Returns True on success.

    On CPython this will raise a RuntimeError when called (importing is fine).
    """
    try:
        import network  # MicroPython module
    except Exception as e:
        raise RuntimeError("Wi‑Fi is only available on MicroPython hardware") from e

    if not ssid:
        log.error("[WiFi] No SSID provided")
        return False

    sta = network.WLAN(network.STA_IF)
    if mac_spoof and hasattr(sta, "config"):
        try:
            sta.config(mac=mac_spoof)
            log.info("[WiFi] MAC spoof set")
        except Exception as e:
            log.warn("[WiFi] MAC spoof failed:", e)

    if not sta.active():
        sta.active(True)

    attempt = 0
    while attempt < retries:
        attempt += 1
        if not sta.isconnected():
            log.info("[WiFi] Connecting to:", ssid, "(attempt", attempt, ")")
            try:
                sta.connect(ssid, password)
            except Exception as e:
                log.warn("[WiFi] connect() error:", e)

        t0 = time.ticks_ms()
        while not sta.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < timeout_s * 1000:
            time.sleep(0.2)
        if sta.isconnected():
            log.info("[WiFi] Connected, ifconfig:", sta.ifconfig())
            return True
        log.warn("[WiFi] Timeout; retrying…")

    log.error("[WiFi] Failed to connect after", retries, "attempts")
    return False

