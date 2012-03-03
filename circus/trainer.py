import os
from threading import Lock

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus import logger

class Trainer(object):

    def __init__(self, shows, endpoint, check_delay=1., ipc_path=None):
        self.shows = shows
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.ipc_path = ipc_path
        self.ctrl = Controller(endpoint, self, self.check_delay,
                self.ipc_path)
        self.pid = os.getpid()
        self._shows_names = {}
        self.alive = True
        self._lock = Lock()
        self.setup()
        logger.info("Starting master on pid %s" % self.pid)

    def setup(self):
        for show in self.shows:
            self._shows_names[show.name] = show

    def start(self):
        # launch flies
        for show in self.shows:
            show.manage_flies()

        while self.alive:
            # manage and reap flies
            for show in self.shows:
                show.reap_flies()
                show.manage_flies()

            # wait for the controller
            self.ctrl.poll()

    def stop(self):
        self.alive = False
        # kill flies
        for show in self.shows:
            show.kill_flies()

        self.ctrl.stop()

    def num_flies(self):
        return sum([len(show) for show in self.shows])

    def num_shows(self):
        return len(self.shows)

    def get_show(self, name):
        return self._shows_names[name]

    def add_show(self, show):
        with self._lock:
            if show.name in self._shows_names:
                raise AlreadyExist("%r already exist" % show.name)
            self.shows.append(show)
            self._shows_names[show.name] = show

    def del_show(self, name):
        with self._lock:
            del self._shows_names[name]
            for i, show in enumerate(self.shows):
                if show.name == name:
                    show.stop()
                    del self.shows[i]
                    break

    ###################
    # commands
    ###################

    def handle_shows(self):
        return ",".join(self._shows_names.keys())

    def handle_flies(self):
        flies = []
        for show in self.shows:
            flies.append("%s: %s" % (show.name, show.handle_flies()))
        return buffer("\n".join(flies))

    def handle_info_shows(self):
        infos = []
        for show in self.shows:
            infos.append("%s:\n" % show.name)
            infos.append("%s\n" % show.handle_info())
        return buffer("".join(infos))

    def handle_reload(self):
        return "ok"

    def handle_winch(self):
        "SIGWINCH handling"
        if os.getppid() == 1 or os.getpgrp() != os.getpid():
            for show in self.shows:
                show.num_flies = 0
                show.kill_flies()
        else:
            # SIGWINCH ignored. Not daemonized
            pass

    def handle_stop_shows(self):
        for show in self.shows:
            show.stop()

        return "ok"

    def handle_start_shows(self):
        for show in self.shows:
            show.start()
        return "ok"

    def handle_restart_shows(self):
        for show in self.shows:
            show.restart()
        return "ok"
