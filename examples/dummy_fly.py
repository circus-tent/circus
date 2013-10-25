#!/usr/bin/env python
import os
import signal
import sys


class DummyFly(object):

    def __init__(self, wid):
        self.wid = wid
        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def handle_quit(self, *args):
        self.alive = False
        sys.exit(0)

    def handle_chld(self, *args):
        return

    def run(self):
        print("hello, fly #%s (pid: %s) is alive" % (self.wid, os.getpid()))

        a = 2
        while self.alive:
            a = a + 200

if __name__ == "__main__":
    DummyFly(sys.argv[1]).run()
