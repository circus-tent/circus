import gevent

from circus.sighandler import SysHandler as _SysHandler


class SysHandler(_SysHandler):

    def _register(self):
        for sig in self.SIGNALS:
            gevent.signal(sig, self.signal, sig)
