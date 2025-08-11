# Enes100 MicroPython Client (ESP32 / Acebott ESP32-Max-V1.0)

This package provides a stable student-facing API to connect an ESP32 to the ENES100 vision system over WebSockets, while keeping the internals maintainable.

## Install (Thonny)
1. Open Thonny with your ESP32 running MicroPython **1.26.0**.
2. In the **Files** pane, create a folder named `Enes100` on the device.
3. Copy the files from this repo into the device so the layout is:

/Enes100
  init.py
  client.py
  constants.py
  config.py
  /net
    init.py
    wifi.py
    websocket_client.py
    /vendor
      uwebsockets.py
  /utils
    init.py
    log.py
    retry.py

## Student usage
Students import the same way:
```py
from Enes100 import enes100

enes100.begin("TeamName", "mission_name_or_id", 5, 101)
while not enes100.isConnected():
 pass

if enes100.isVisible():
 x = enes100.getX()
 y = enes100.getY()
 th = enes100.getTheta()
 enes100.print("Pose:", x, y, th)