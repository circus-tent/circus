import signal
import traceback
import sys

from circus import logger
from circus.client import make_json


class SysHandler(object):

    SIGNALS = [getattr(signal, "SIG%s" % x) for x in
               "HUP QUIT INT TERM WINCH".split()]

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )

    def __init__(self, controller):
        self.controller = controller

        # init signals
        logger.info('Registering signals...')
        self._old = {}
        self._register()

    def stop(self):
        for sig, callback in self._old.items():
            try:
                signal.signal(sig, callback)
            except ValueError:
                pass

    def _register(self):
        for sig in self.SIGNALS:
            self._old[sig] = signal.getsignal(sig)
            signal.signal(sig, self.signal)

        # Don't let SIGQUIT and SIGUSR1 disturb active requests
        # by interrupting system calls
        if hasattr(signal, 'siginterrupt'):  # python >= 2.6
            signal.siginterrupt(signal.SIGQUIT, False)
            signal.siginterrupt(signal.SIGUSR1, False)

    def signal(self, sig, frame=None):
        signame = self.SIG_NAMES.get(sig)
        logger.info('Got signal SIG_%s' % signame.upper())

        if signame is not None:
            try:
                handler = getattr(self, "handle_%s" % signame)
                handler()
            except AttributeError:
                pass
            except Exception as e:
                tb = traceback.format_exc()
                logger.error("error: %s [%s]" % (e, tb))
                sys.exit(1)

    def handle_int(self):
        self.controller.dispatch((None, make_json("quit")))

    def handle_term(self):
        self.controller.dispatch((None, make_json("quit")))

    def handle_quit(self):
        self.controller.dispatch((None, make_json("quit")))

    def handle_winch(self):
        pass

    def handle_hup(self):
        self.controller.dispatch((None, make_json("reload", graceful=True)))
