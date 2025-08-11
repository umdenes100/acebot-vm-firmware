# Thin, blocking WebSocket wrapper around vendor uwebsockets for MicroPython
import time
from .vendor import uwebsockets


class WSClient:
    def __init__(self, url):
        self._url = url
        self._ws = uwebsockets.connect(url)

    def send(self, text):
        return self._ws.send(text)

    def recv(self, timeout_ms=None):
        # Simple poll loop; vendor lib is typically blocking without timeout
        if timeout_ms is None:
            return self._ws.recv()
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            try:
                return self._ws.recv()
            except Exception:
                # No message ready; small sleep to yield
                time.sleep(0.05)
        return None

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass

