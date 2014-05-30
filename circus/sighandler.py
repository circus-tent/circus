import signal
import traceback
import sys

from circus import logger
from circus.client import make_json
from circus.util import IS_WINDOWS


class SysHandler(object):

    _SIGNALS_NAMES = ("ILL ABRT BREAK INT TERM" if IS_WINDOWS else
                      "HUP QUIT INT TERM WINCH")

    SIGNALS = [getattr(signal, "SIG%s" % x) for x in _SIGNALS_NAMES.split()]

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

    def quit(self):
        # We need to transfer the control to the loop's thread
        self.controller.loop.add_callback_from_signal(
            self.controller.dispatch, (None, make_json("quit"))
        )

    def reload(self):
        # We need to transfer the control to the loop's thread
        self.controller.loop.add_callback_from_signal(
            self.controller.dispatch,
            (None, make_json("reload", graceful=True))
        )

    def handle_int(self):
        self.quit()

    def handle_term(self):
        self.quit()

    def handle_quit(self):
        self.quit()

    def handle_ill(self):
        self.quit()

    def handle_abrt(self):
        self.quit()

    def handle_break(self):
        self.quit()

    def handle_winch(self):
        pass

    def handle_hup(self):
        self.reload()
