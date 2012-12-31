import signal
import traceback
import sys

from circus import logger
from client import make_json


class SysHandler(object):

    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM WINCH".split()
    )

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )

    def __init__(self, controller):
        self.controller = controller

        # init signals
        map(lambda s: signal.signal(s, self.signal), self.SIGNALS)

        # Don't let SIGQUIT and SIGUSR1 disturb active requests
        # by interrupting system calls
        if hasattr(signal, 'siginterrupt'):  # python >= 2.6
            signal.siginterrupt(signal.SIGQUIT, False)
            signal.siginterrupt(signal.SIGUSR1, False)

    def signal(self, sig, frame):
        signame = self.SIG_NAMES.get(sig)
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
        self.controller.add_job(None, make_json("quit"))

    def handle_term(self):
        self.controller.add_job(None, make_json("quit"))

    def handle_quit(self):
        self.controller.add_job(None, make_json("quit"))

    def handle_winch(self):
        pass

    def handle_hup(self):
        self.controller.add_job(None, make_json("reload", graceful=True))
