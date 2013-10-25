import threading
from threading import (_active_limbo_lock, _limbo, _active, _sys, _trace_hook,
                       _profile_hook, _format_exc)


debugger = False
try:
    import pydevd
    debugger = pydevd.GetGlobalDebugger()
except ImportError:
    pass

if not debugger:
    # see http://bugs.python.org/issue1596321
    if hasattr(threading.Thread, '_Thread__stop'):
        def _bootstrap_inner(self):
            try:
                self._set_ident()
                self._Thread__started.set()
                with _active_limbo_lock:
                    _active[self._Thread__ident] = self
                    del _limbo[self]

                if _trace_hook:
                    _sys.settrace(_trace_hook)
                if _profile_hook:
                    _sys.setprofile(_profile_hook)

                try:
                    self.run()
                except SystemExit:
                    pass
                except:
                    if _sys:
                        _sys.stderr.write("Exception in thread %s:\n%s\n" %
                                          (self.name, _format_exc()))
                    else:
                        exc_type, exc_value, exc_tb = self._exc_info()
                        try:
                            self._stderr.write(
                                "Exception in thread " + self.name + " (most "
                                "likely raised during interpreter shutdown):")

                            self._stderr.write("Traceback (most recent call "
                                               "last):")
                            while exc_tb:
                                self._stderr.write(
                                    '  File "%s", line %s, in %s' %
                                    (exc_tb.tb_frame.f_code.co_filename,
                                        exc_tb.tb_lineno,
                                        exc_tb.tb_frame.f_code.co_name))

                                exc_tb = exc_tb.tb_next
                            self._stderr.write("%s: %s" %
                                               (exc_type, exc_value))
                        finally:
                            del exc_type, exc_value, exc_tb
                finally:
                    pass
            finally:
                with _active_limbo_lock:
                    self._Thread__stop()
                    try:
                        del _active[self._Thread__ident]
                    except:
                        pass

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

        threading.Thread._Thread__bootstrap_inner = _bootstrap_inner
        threading.Thread._Thread__delete = _delete
        threading.Thread._Thread__stop_old = threading.Thread._Thread__stop
        threading.Thread._Thread__stop = _stop
    else:
        def _bootstrap_inner(self):  # NOQA
            try:
                self._set_ident()
                self._started.set()
                with _active_limbo_lock:
                    _active[self._ident] = self
                    del _limbo[self]

                if _trace_hook:
                    _sys.settrace(_trace_hook)
                if _profile_hook:
                    _sys.setprofile(_profile_hook)

                try:
                    self.run()
                except SystemExit:
                    pass
                except:
                    if _sys:
                        _sys.stderr.write("Exception in thread %s:\n%s\n" %
                                          (self.name, _format_exc()))
                    else:
                        exc_type, exc_value, exc_tb = self._exc_info()
                        try:
                            self._stderr.write(
                                "Exception in thread " + self.name + " (most "
                                "likely raised during interpreter shutdown):")

                            self._stderr.write("Traceback (most recent call "
                                               "last):")
                            while exc_tb:
                                self._stderr.write(
                                    '  File "%s", line %s, in %s' %
                                    (exc_tb.tb_frame.f_code.co_filename,
                                        exc_tb.tb_lineno,
                                        exc_tb.tb_frame.f_code.co_name))

                                exc_tb = exc_tb.tb_next
                            self._stderr.write("%s: %s" %
                                               (exc_type, exc_value))
                        finally:
                            del exc_type, exc_value, exc_tb
                finally:
                    pass
            finally:
                with _active_limbo_lock:
                    self._stop()
                    try:
                        del _active[self._ident]
                    except:
                        pass

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

        threading.Thread._bootstrap_inner = _bootstrap_inner
        threading.Thread._delete = _delete
        threading.Thread._stop_old = threading.Thread._stop
        threading.Thread._stop = _stop
