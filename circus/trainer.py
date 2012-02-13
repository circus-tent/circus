# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import errno
import os
import sys
import time

from circus.controller import Controller


class Trainer(object):

    def __init__(self, shows, check_delay, endpoint, ipc_path):
        self.shows = shows
        self.check_delay = check_delay
        self.ipc_path = ipc_path
        self.ctrl = Controller(endpoint, self, self.check_delay,
                self.ipc_path)
        self.pid = os.getpid()

        self._shows_names = {}
        self.setup()
        print "Starting master on pid %s" % self.pid

    def setup(self):
        for show in self.shows:
            self._shows_names[show.name] = show

    def get_show(self, name):
        return self._shows_names[name]

    def list_shows(self):
        return ",".join(self._shows_names.keys())

    def handle_reload(self):
        return "ok"

    def handle_quit(self):
        self.halt()

    def handle_winch(self):
        "SIGWINCH handling"
        if os.getppid() == 1 or os.getpgrp() != os.getpid():
            for show in self.shows:
                show.num_flies = 0
                show.kill_flies()
        else:
            # SIGWINCH ignored. Not daemonized
            pass

    def num_flies(self):
        l = 0
        for show in self.shows:
            l += len(show)
        return l

    def run(self):
        # launch flies
        for show in self.shows:
            show.manage_flies()

        while True:
            # manage and reap flies
            for show in self.shows:
                show.reap_flies()
                show.manage_flies()

            # wait for the controller
            self.ctrl.poll()

    def halt(self, exit_code=0):
        self.terminate()
        sys.exit(exit_code)

    def terminate(self):
        # kill flies
        for show in self.shows:
            show.kill_flies()

        self.ctrl.terminate()
