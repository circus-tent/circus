from . import _patch  # NOQA
from threading import Thread, RLock, Timer  # NOQA
try:
    from _thread import get_ident
except ImportError:
    from thread import get_ident  # NOQA
