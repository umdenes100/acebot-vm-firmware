import network
import time
import machine
import _thread
import uasyncio as asyncio
import sys
sys.path.append('/lib/enes100')
import uwebsockets as web
import ujson as json

import wifi

#  make a dict 
mission_stuff = {
    # Mission Types
    'CRASH_SITE' : 0,
    'DATA' : 1,
    'MATERIAL' : 2,
    'FIRE' : 3,
    'WATER' : 4,
    'SEED' : 5,
    'HYDROGEN' : 6,

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
    
    # Hydrogen Mission
    'VOLTAGE_OUTPUT' : 0,
    'LED_COLOR' : 1,
    'VOLTAGE_1' : 0,
    'VOLTAGE_2' : 1,
    'VOLTAGE_3' : 2,
    'VOLTAGE_4' : 3,
    'VOLTAGE_5' : 4,
    'WHITE' : 0,
    'RED' : 1,
    'YELLOW' : 2,
    'GREEN' : 3,
    'BLUE' : 4,
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
    
    # sends packets of info to VS through websocket
    def _send_packet(self, packet):
        if self.ws:
            self.ws.send(json.dumps(packet))
    
    # runs the websocket, receives the data from VS and saves it to appropriate vars
    def _websocket_client(self):
        # TODO -> reconnect functionality
        while True:
            msg = self.ws.recv()
            if msg:
                data = json.loads(msg)
#                 print("Received:", data)
                if data.get("op") == "aruco":
                    aruco = data.get("aruco", {})
                    self.is_visible = aruco.get("visible", False)
                    self.x = aruco.get("x", -1.0)
                    self.y = aruco.get("y", -1.0)
                    self.theta = aruco.get("theta", -1.0)
    
    # begin statement used to gather basic info from teams, connect to wifi, init websocket and get it running
    def begin(self, team_name, mission_type, aruco_id, room_num):
        self.team_name = team_name
        self.mission_type = mission_stuff[mission_type.upper()]
        self.aruco_id = aruco_id
        self.room_num = room_num
        
        WS_URL = {
            '1120' : "ws://10.112.9.33:7755",
            '1116' : "ws://10.112.9.113:7755",
            '1201' : "ws://10.112.9.114:7755",
            '1215' : "ws://10.112.9.115:7755",
            '0' : "ws://10.112.9.115:7755"
        }

        # Connect to WiFi
        wifi.connect()
        
        # Connect to VS
        self.ws = web.connect(WS_URL[str(room_num)])
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
    def is_connected(self):
        return self.ws.open
    
# create instance... what's used by the students. Is the self parameter
enes100 = Enes100()
