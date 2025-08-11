import network
import time
import machine
import _thread
import uasyncio as asyncio
import sys
#sys.path.append('/lib/enes100')
import uwebsockets as web
import ujson as json

# TEMPORARY: Spoof MAC
import ubinascii
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(mac=b'\xBC\xDD\xC2\x24\xA8\x6C')
print("Spoofed MAC:", ubinascii.hexlify(sta.config('mac'), ':').decode())
  
# WebSocket Server
WS_URL = "ws://10.112.9.33:7755"

#  make a dict 
mission_stuff = {
    # Mission Types
    'CRASH_SITE' : 0,
    'DATA' : 1,
    'MATERIAL' : 2,
    'FIRE' : 3,
    'WATER' : 4,
    'SEED' : 5,

    # Crash Mission
    'DIRECTION' : 0,
    'LENGTH' : 1,
    'HEIGHT': 2,
    'NORMAL_X' : 0,
    'NORMAL_Y' : 1,

    # Data Mission
    'CYCLE' : 0,
    'MAGNETISM' : 1,
    'MAGNETIC' : 0,
    'NOT_MAGNETIC' : 1,

    # Materials Mission
    'WEIGHT' : 0,
    'MATERIAL_TYPE' : 1,
    'FOAM' : 0,
    'PLASTIC' : 1,
    'HEAVY' : 0,
    'MEDIUM' : 1,
    'LIGHT' : 2,

    # Fire Mission
    'NUM_CANDLES' : 0,
    'TOPOGRAPHY' : 1,
    'TOP_A' : 0,
    'TOP_B' : 1,
    'TOP_C' : 2,

    # Water Mission
    'DEPTH' : 0,
    'WATER_TYPE' : 1,
    'FRESH_UNPOLLUTED' : 0,
    'FRESH_POLLUTED' : 1,
    'SALT_UNPOLLUTED' : 2,
    'SALT_POLLUTED' : 3,

    # Seed Mission
    'LOCATION' : 0,
    'A' : 'A',
    'B' : 'B',
    'C' : 'C',
    'D' : 'D',
}
    


class Enes100:
    # initializes variables needed for the Enes100 instance
    def __init__(self):
        self.team_name = ''
        self.mission_type = 0
        self.aruco_id = 0
        self.room_num = 0
        
        self.ws = None
        self.x = -1.0
        self.y = -1.0
        self.theta = -1.0
        self.is_visible = False
        
        self._ws_thread_running = False
    
    # sends packets of info to VS through websocket
    def _send_packet(self, packet):
        if not self.ws:
            print("WebSocket not connected.")
            self._attempt_reconnect()
            return

        try:
            self.ws.send(json.dumps(packet))
        except Exception as e:
            print("WebSocket send error:", e)
            self.ws = None  # Invalidate
            self._attempt_reconnect()
            
    def _resend_begin_packet(self):
        if not self.team_name:
            print("No team name set. Skipping begin packet resend.")
            return

        packet = {
            "op": "begin",
            "teamName": self.team_name,
            "aruco": self.aruco_id,
            "teamType": self.mission_type
        }
        print("Resending begin packet...")
        self._send_packet(packet)

    def _attempt_reconnect(self):
        import gc
        print("Attempting to reconnect to WebSocket...")

        # Clean up previous state
        try:
            if self.ws:
                self.ws.close()
        except:
            pass

        self.ws = None
        self._ws_thread_running = False
        gc.collect()
        time.sleep(0.1)

        for attempt in range(5):
            try:
                ws_temp = web.connect(WS_URL)

                # Test connection
                try:
                    ws_temp.send(json.dumps({"op": "ping"}))
                except Exception as e:
                    print(f"Ping test failed on attempt {attempt + 1}:", repr(e))
                    ws_temp = None
                    raise e

                print(f"Reconnected on attempt {attempt + 1}")
                self.ws = ws_temp

                # Re-send begin packet
                self._resend_begin_packet()

                if not self._ws_thread_running:
                    _thread.start_new_thread(self._websocket_client, ())

                return

            except Exception as e:
                print(f"Reconnect attempt {attempt + 1} failed:", repr(e))
                self.ws = None
                time.sleep(1)

        print("Failed to reconnect after 5 attempts.")
    
    # runs the websocket, receives the data from VS and saves it to appropriate vars
    def _websocket_client(self):
        self._ws_thread_running = True
        try:
            while True:
                if not self.ws:
                    break
                try:
                    msg = self.ws.recv()
                    if msg:
                        data = json.loads(msg)
                        if data.get("op") == "aruco":
                            aruco = data.get("aruco", {})
                            self.is_visible = aruco.get("visible", False)
                            self.x = aruco.get("x", -1.0)
                            self.y = aruco.get("y", -1.0)
                            self.theta = aruco.get("theta", -1.0)
                except Exception as parse_err:
                    print("WebSocket receive/parse error:", repr(parse_err))
                    break
        except Exception as ws_err:
            print("WebSocket thread error:", repr(ws_err))
        finally:
            self._ws_thread_running = False
            try:
                if self.ws:
                    self.ws.close()
            except:
                pass
            self.ws = None
            import gc
            gc.collect()
            time.sleep(0.1)
            self._attempt_reconnect()

    
    # begin statement used to gather basic info from teams, connect to wifi, init websocket and get it running
    def begin(self, team_name, mission_type, aruco_id, room_num):
        self.team_name = team_name
        self.mission_type = mission_stuff[mission_type.upper()]
        self.aruco_id = aruco_id
        self.room_num = room_num
        
        # Connect to WiFi
        ssid = f'umd-iot'
        key = 'JTiKnCm4gs6D'
        print(f'Connecting to {ssid}...')
        
        sta_if = network.WLAN(network.WLAN.IF_STA)
        if not sta_if.isconnected():
            sta_if.active(True)
            sta_if.connect(ssid, key)
            while not sta_if.isconnected():
                time.sleep(0.01)
        #print('Connected to WiFi')
        
        # Connect to VS
        self.ws = web.connect(WS_URL)
        #print("Connected to WebSocket Server")
        
        # Send begin statement to VS
        packet = {
            "op": "begin",
            "teamName": self.team_name,
            "aruco": self.aruco_id,
            "teamType": self.mission_type
        }
        self._send_packet(packet)
        
        _thread.start_new_thread(self._websocket_client, ())
        
    # handles the creation and delivery of the mission packet
    def mission(self, mission_call, message):
        mission_call = mission_stuff[mission_call.upper()]
        if (type(message) == str):
            message = mission_stuff[message.upper()]
            
        packet = {
            "op": "mission",
            "teamName": self.team_name,
            "type": mission_call,
            "message": message
        }
        self._send_packet(packet)
        
    # handles the creation and delivery of the mission packet
    def print(self, message):
        packet = {
            "op": "print",
            "teamName": self.team_name,
            "message": str(message) + '\n'
        }
        self._send_packet(packet)
        #print(json.dumps(packet))
        
    # checks if device is still connected to VS through websocket
    def isConnected(self):
        if not self.ws:
            return False
        try:
            self.ws.send(json.dumps({"op": "ping"}))
            return True
        except Exception as e:
            print("WebSocket ping failed:", repr(e))
            self.ws = None
            return False
    def _get_with_retry(self, attr_name, fallback):
        """Helper to retry fetching a field (x, y, theta, visibility) up to 5 times."""
        if not self.is_connected():
            print("WebSocket not connected.")
            return fallback

        for i in range(5):
            value = getattr(self, attr_name)
            if value != fallback:
                return value
            time.sleep(0.025)  # 25ms delay
        return getattr(self, attr_name)

    def getX(self):
        """Returns the latest x position, retrying if it's invalid (-1.0)."""
        return self._get_with_retry('x', -1.0)

    def getY(self):
        """Returns the latest y position, retrying if it's invalid (-1.0)."""
        return self._get_with_retry('y', -1.0)

    def getTheta(self):
        """Returns the latest theta, retrying if it's invalid (-1.0)."""
        return self._get_with_retry('theta', -1.0)

    def isVisible(self):
        """Returns the visibility of the aruco marker, retrying if False."""
        return self._get_with_retry('is_visible', False)

    
# create instance... what's used by the students. Is the self parameter
enes100 = Enes100()