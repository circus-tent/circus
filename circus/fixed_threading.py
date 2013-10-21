from . import _patch  # NOQA
from threading import Thread, RLock, Timer  # NOQA
try:
    from threading import get_ident  # NOQA
except ImportError:
    from thread import get_ident  # NOQA
