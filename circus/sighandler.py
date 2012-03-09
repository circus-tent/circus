import signal
import traceback
import sys

from circus import logger


class SysHandler(object):

    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM WINCH CHLD".split()
    )

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )

    def __init__(self, trainer):
        self.trainer = trainer

        # init signals
        map(lambda s: signal.signal(s, self.signal), self.SIGNALS)

    def signal(self, sig, frame):
        signame = self.SIG_NAMES.get(sig)
        if signame is not None:
            try:
                handler = getattr(self, "handle_%s" % signame)
                handler()
            except AttributeError:
                pass
            except Exception, e:
                tb = traceback.format_exc()
                logger.error("error: %s [%s]" % (e, tb))
                sys.exit(1)

    def handle_chld(self):
        pass

    def handle_int(self):
        self.trainer.stop(False)

    def handle_term(self):
        self.trainer.stop(False)

    def handle_quit(self):
        self.trainer.stop()

    def handle_winch(self):
        pass

    def handle_hup(self):
        self.trainer.reload()
