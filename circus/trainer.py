import logging
import os
import sys
from threading import Lock
from functools import wraps

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus import logger
from circus.util import debuglog


class Trainer(object):

    def __init__(self, shows, endpoint, check_delay=1., prereload_fn=None):
        self.shows = shows
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.prereload_fn = prereload_fn
        self.ctrl = Controller(endpoint, self, self.check_delay)
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
        logger.debug('Starting the controller')

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

    def stop(self, graceful=True):
        logger.debug('Stopping the trainer')
        self.alive = False
        # kill flies
        for show in self.shows:
            show.stop(graceful=graceful)

        self.ctrl.stop()
        logger.debug('Trainer stopped')

    def reload(self):
        logger.debug('Reloading the controller')

        if self.prereload_fn is not None:
            self.prereload_fn(self)

        # reopen log files
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.acquire()
                handler.stream.close()
                handler.stream = open(handler.baseFilename,
                        handler.mode)
                handler.release()

        # gracefully reload shows
        for show in self.shows:
            show.reload()

    def num_flies(self):
        return sum([len(show) for show in self.shows])

    def num_shows(self):
        return len(self.shows)

    def get_show(self, name):
        return self._shows_names[name]

    def add_show(self, show):
        logger.debug('Adding a %r show' % show.name)

        with self._lock:
            if show.name in self._shows_names:
                raise AlreadyExist("%r already exist" % show.name)
            self.shows.append(show)
            self._shows_names[show.name] = show

    def del_show(self, name):
        logger.debug('Deleting %r show' % name)

        with self._lock:
            # remove the show from the list
            show = self._shows_names.pop(name)
            del self.shows[self.shows.index(show)]

            # stop the show
            show.stop()

    ###################
    # commands
    ###################

    @debuglog
    def handle_numflies(self):
        return str(self.num_flies())

    @debuglog
    def handle_numshows(self):
        return str(self.num_shows())

    @debuglog
    def handle_shows(self):
        return ",".join(self._shows_names.keys())

    @debuglog
    def handle_flies(self):
        flies = []
        for show in self.shows:
            flies.append("%s: %s" % (show.name, show.handle_flies()))
        return buffer("\n".join(flies))

    @debuglog
    def handle_info_shows(self):
        infos = []
        for show in self.shows:
            infos.append("%s:\n" % show.name)
            infos.append("%s\n" % show.handle_info())
        return buffer("".join(infos))

    @debuglog
    def handle_reload(self):
        self.reload()
        return "ok"

    @debuglog
    def handle_stop_shows(self):
        for show in self.shows:
            show.stop()
        return "ok"

    @debuglog
    def handle_start_shows(self):
        for show in self.shows:
            show.start()
        return "ok"

    @debuglog
    def handle_restart_shows(self):
        for show in self.shows:
            show.restart()
        return "ok"
