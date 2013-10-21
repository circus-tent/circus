from . import _patch
from threading import Thread, RLock, Timer
try:
    from threading import get_ident
except ImportError:
    from thread import get_ident
