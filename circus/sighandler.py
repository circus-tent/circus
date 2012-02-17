# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.  The
# Secondary License is the Apache License 2.0. You may obtain a copy of
# the Apache License 2 at http://www.apache.org/licenses/LICENSE-2.0.

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
            "term": "quit",
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
