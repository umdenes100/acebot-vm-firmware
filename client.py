import json
import time
import _thread
from .config import DEBUG, WS_URL, WIFI_SSID, WIFI_PASSWORD, MAC_SPOOF
from .utils import log
from .net.wifi import ensure_wifi
from .net.websocket_client import WSClient
from . import constants


class Enes100:
    def __init__(self):
        # Pose/state updated from vision system
        self._x = 0.0
        self._y = 0.0
        self._theta = 0.0
        self._is_visible = False

        # Connection members
        self._wifi_ok = False
        self._ws = None
        self._ws_connected = False
        self._ws_thread_started = False
        self._stop = False

        # Student-provided / begin() parameters
        self._team_name = None
        self._mission = None
        self._aruco_id = None
        self._room_num = None

        # Locks
        self._state_lock = _thread.allocate_lock()
        self._conn_lock = _thread.allocate_lock()

    # --- Public API (names preserved) ---
    def begin(self, team_name, mission_type, aruco_id, room_num):
        """
        Initialize Wi‑Fi and WebSocket connection. Keeps legacy signature.
        """
        self._team_name = team_name
        self._mission = constants.normalize_mission(mission_type)
        self._aruco_id = aruco_id
        self._room_num = room_num

        log.info("[Enes100] begin(): connecting Wi‑Fi…")
        self._wifi_ok = ensure_wifi(WIFI_SSID, WIFI_PASSWORD, mac_spoof=MAC_SPOOF)
        if not self._wifi_ok:
            log.error("[Enes100] Wi‑Fi failed. Check SSID/password in config.py")
            return False

        # Connect WS (non-blocking loop in a thread)
        if not self._ws_thread_started:
            self._stop = False
            _thread.start_new_thread(self._ws_loop, ())
            self._ws_thread_started = True
        else:
            log.debug("[Enes100] WS thread already started")
        return True

    def mission(self, mission_type):
        """Return a normalized mission identifier; accepts enum/int/str."""
        return constants.normalize_mission(mission_type)

    def print(self, *args):
        """Send a printable message back to the vision system (op='print')."""
        try:
            msg = " ".join(str(a) for a in args)
            self._send_json({"op": "print", "msg": msg, "team": self._team_name})
        except Exception as e:
            log.debug("[Enes100] print() send failed:", e)

    def isConnected(self):
        """True if both Wi‑Fi is up and WS is open."""
        return bool(self._wifi_ok and self._ws_connected)

    def getX(self):
        with self._state_lock:
            return self._x

    def getY(self):
        with self._state_lock:
            return self._y

    def getTheta(self):
        with self._state_lock:
            return self._theta

    def isVisible(self):
        with self._state_lock:
            return self._is_visible

    # --- Internal helpers ---
    def _send_json(self, obj):
        with self._conn_lock:
            ws = self._ws
        if not ws:
            return False
        try:
            ws.send(json.dumps(obj))
            return True
        except Exception as e:
            log.debug("[Enes100] WS send error:", e)
            return False

    def _handle_message(self, text):
        try:
            msg = json.loads(text)
        except Exception:
            return

        op = msg.get("op")
        if op == "aruco":
            # Expected payload: { op:"aruco", x: float, y: float, theta: float, visible: bool }
            with self._state_lock:
                self._x = float(msg.get("x", self._x))
                self._y = float(msg.get("y", self._y))
                self._theta = float(msg.get("theta", self._theta))
                self._is_visible = bool(msg.get("visible", self._is_visible))
        elif op == "pong":
            # no-op keepalive
            pass
        else:
            # Unknown op; ignore quietly (keep student stdout clean)
            if DEBUG:
                log.debug("[Enes100] unknown op:", op)

    def _announce(self):
        # Let the server know who we are (shape to be aligned with your backend)
        payload = {
            "op": "hello",
            "team": self._team_name,
            "mission": self._mission,
            "aruco": self._aruco_id,
            "room": self._room_num,
        }
        self._send_json(payload)

    def _ws_loop(self):
        backoff = 0.5
        while not self._stop:
            try:
                log.info("[Enes100] connecting WS…", WS_URL)
                ws = WSClient(WS_URL)
                with self._conn_lock:
                    self._ws = ws
                    self._ws_connected = True
                log.info("[Enes100] WS connected")
                backoff = 0.5

                # Announce/handshake
                self._announce()

                last_ping = time.ticks_ms()
                while not self._stop:
                    # Keepalive ping every ~5s
                    if time.ticks_diff(time.ticks_ms(), last_ping) > 5000:
                        self._send_json({"op": "ping"})
                        last_ping = time.ticks_ms()

                    # Block waiting for next message with internal timeout
                    text = ws.recv(timeout_ms=2000)
                    if text:
                        self._handle_message(text)

                # graceful stop requested
                try:
                    ws.close()
                except Exception:
                    pass
                with self._conn_lock:
                    self._ws = None
                    self._ws_connected = False
                return

            except Exception as e:
                with self._conn_lock:
                    self._ws = None
                    self._ws_connected = False
                log.warn("[Enes100] WS reconnect in", backoff, "s (", e, ")")
                time.sleep(backoff)
                # Exponential backoff up to 5s
                backoff = min(backoff * 2, 5.0)

    # Optional: allow library users to stop background thread if needed
    def _stop_ws(self):
        self._stop = True
