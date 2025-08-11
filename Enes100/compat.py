"""
Compatibility helpers so this package can be imported on CPython
while still working on MicroPython hardware.
"""

import sys
import time as _time

MICROPY = (getattr(sys.implementation, "name", "") == "micropython")

# --- ticks_* shims ---
if MICROPY:
    from time import ticks_ms, ticks_diff, ticks_add  # type: ignore
else:
    # Emulate MicroPython ticks on CPython
    # Using monotonic_ns to avoid time going backwards.
    def ticks_ms():
        return int(_time.monotonic_ns() // 1_000_000)

    def ticks_add(ticks, delta_ms):
        return ticks + int(delta_ms)

    def ticks_diff(ticks1, ticks2):
        # MicroPython returns signed wrap-around difference.
        return int(ticks1 - ticks2)
