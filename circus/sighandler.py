import signal
import traceback
import zmq

from circus import logger

class SysHandler(object):

    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM WINCH CHLD".split()
    )

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
    )

    CMD_MAP = {
            "hup": "reload",
            "int": "quit",
            "term": "quit",
            "quit": "quit",
            "winch": "winch"
    }

    def __init__(self, trainer):
        self.trainer = trainer

        # init signals
        map(lambda s: signal.signal(s, self.signal), self.SIGNALS)

    def signal(self, sig, frame):
        signame = self.SIG_NAMES.get(sig)
        if signame is not None and signame in self.CMD_MAP:
            cmd = self.CMD_MAP[signame]
            try:
                handler = getattr(self, "handle_%s" % cmd)
                handler()
            except Exception, e:
                tb = traceback.format_exc()
                logger.error("error: %s [%s]" % (e, tb))
                sys.exit(1)

    def handle_chld(self, *args):
        pass

    def handle_quit(self):
        self.trainer.stop()

    def handle_winch(self):
        pass

    def handle_reload(self):
        self.trainer.reload()
