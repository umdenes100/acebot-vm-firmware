try:
    from ..config import DEBUG
except Exception:
    DEBUG = False  # Safe default if config import ever fails early


def _pfx(level):
    return "[LOG]" if level == "" else "[{}]".format(level)


def debug(*args):
    if DEBUG:
        print(_pfx("DBG"), *args)


def info(*args):
    print(_pfx("INF"), *args)


def warn(*args):
    print(_pfx("WRN"), *args)


def error(*args):
    print(_pfx("ERR"), *args)

