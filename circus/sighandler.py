import signal
import zmq


class SysHandler(object):

    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM WINCH".split()
    )

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
    )

    CMD_MAP = {
            "hup": "reload",
            "int": "quit",
            "quit": "quit"
    }

    def __init__(self, ipc_path):
        # set zmq socket
        self.ctx = zmq.Context()
        self.skt = self.ctx.socket(zmq.REQ)
        self.skt.connect("ipc://%s" % ipc_path)

        # init signals
        map(lambda s: signal.signal(s, self.signal), self.SIGNALS)
        signal.signal(signal.SIGCHLD, self.handle_chld)

    def signal(self, sig, frame):
        if sig in self.SIG_NAMES:
            signame = self.SIG_NAMES.get(sig)
            self.skt.send(self.CMD_MAP[signame])

    def handle_chld(self, *args):
        pass

    def terminate(self):
        try:
            self.ctx.destroy(0)
        except:
            # XXX log
            pass
