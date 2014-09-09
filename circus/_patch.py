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
    if hasattr(threading.Thread, '_Thread__stop'):
        # see http://bugs.python.org/issue1596321
        def _delete(self):
            try:
                with _active_limbo_lock:
                    del _active[self._Thread__ident]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise

        # http://bugs.python.org/issue14308
        def _stop(self):
            # DummyThreads delete self.__block, but they have no waiters to
            # notify anyway (join() is forbidden on them).
            if not hasattr(self, '_Thread__block'):
                return
            self._Thread__stop_old()

        threading.Thread._Thread__delete = _delete
        threading.Thread._Thread__stop_old = threading.Thread._Thread__stop
        threading.Thread._Thread__stop = _stop
    else:
        # see http://bugs.python.org/issue1596321
        def _delete(self):  # NOQA
            try:
                with _active_limbo_lock:
                    del _active[self._ident]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise

        # http://bugs.python.org/issue14308
        def _stop(self):  # NOQA
            # DummyThreads delete self.__block, but they have no waiters to
            # notify anyway (join() is forbidden on them).
            if not hasattr(self, '_block'):
                return
            self._stop_old()

        threading.Thread._delete = _delete
        threading.Thread._stop_old = threading.Thread._stop
        threading.Thread._stop = _stop
