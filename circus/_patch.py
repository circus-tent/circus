import threading
from threading import _active_limbo_lock, _active, _sys


debugger = False
try:
    # noinspection PyUnresolvedReferences
    import pydevd
    debugger = pydevd.GetGlobalDebugger()
except ImportError:
    pass

if not debugger:
    # see http://bugs.python.org/issue1596321
    if hasattr(threading.Thread, '_Thread__delete'):
        def _delete(self):
            try:
                with _active_limbo_lock:
                    del _active[self._Thread__ident]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise

        threading.Thread._Thread__delete = _delete
    else:
        def _delete(self):  # NOQA
            try:
                with _active_limbo_lock:
                    del _active[self._ident]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise

        threading.Thread._delete = _delete
