# Tiny helpers if we later want retry/backoff utilities.

import time


def sleep_backoff(cur, max_val=5.0):
    time.sleep(cur)
    return min(cur * 2, max_val)
