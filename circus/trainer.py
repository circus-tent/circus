import errno
import logging
import os
import sys
from threading import Lock
import time
from functools import wraps

import zmq

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus.flapping import Flapping
from circus import logger
from circus.show import Show
from circus.util import debuglog


class Trainer(object):
    """Class used to control a list of shows.

    Options:

    - **shows**: a list of Show objects
    - **endpoint**: the controller ZMQ endpoint
    - **pubsub_endpoint**: the pubsub endpoint
    - **check_delay**: the delay between two controller points (defaults: 1 s)
    - **prereload_fn**: callable that will be executed on each reload (defaults:
      None)
    """
    def __init__(self, shows, endpoint, pubsub_endpoint, check_delay=1.,
                 prereload_fn=None):

        self.shows = shows
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.prereload_fn = prereload_fn
        self.pubsub_endpoint = pubsub_endpoint
        self.context = zmq.Context()

        self.ctrl = Controller(self.context, endpoint, self, self.check_delay)
        self.flapping = Flapping(endpoint, pubsub_endpoint, check_delay)

        self.pid = os.getpid()
        self._shows_names = {}
        self.alive = True
        self._lock = Lock()
        self._setup()
        logger.info("Starting master on pid %s" % self.pid)

    def _setup(self):
        # set pubsub endpoint
        self.pubsub_io  = self.context.socket(zmq.PUB)
        self.pubsub_io.bind(self.pubsub_endpoint)

        for show in self.shows:
            self._shows_names[show.name.lower()] = show
            show.pubsub_io = self.pubsub_io

    @debuglog
    def start(self):
        """Starts all the shows.

        The start command is an infinite loop that waits
        for any command from a client and that watches all the
        flies and restarts them if needed.
        """

        # start flapping
        self.flapping.start()

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

    @debuglog
    def stop(self, graceful=True):
        """Stops all shows and their flies.

        Options:

        - **graceful**: sends a SIGTERM to every fly and waits a bit
          before killing it (default: True)
        """
        if not self.alive:
            return

        self.alive = False

        self.flapping.stop()

        # kill flies
        for show in self.shows:
            show.stop(graceful=graceful)

        time.sleep(0.5)
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise

    @debuglog
    def reload(self):
        """Reloads everything.

        Run the :func:`prereload_fn` callable if any, then gracefuly
        reload all shows.
        """
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

    def numflies(self):
        """Return the number of flies running across all shows."""
        return sum([len(show) for show in self.shows])

    def num_shows(self):
        """Return the number of shows."""
        return len(self.shows)

    def get_show(self, name):
        """Return the show *name*."""
        return self._shows_names[name]

    def add_show(self, name, cmd):
        """Adds a show.

        Options:

        - **name**: name of the show to add
        - **cmd**: command to run.
        """
        with self._lock:
            if name in self._shows_names:
                raise AlreadyExist("%r already exist" % show.name)

            show = Show(name, cmd, stopped=True)
            show.pubsub_io = self.pubsub_io
            self.shows.append(show)
            self._shows_names[show.name.lower()] = show

    def del_show(self, name):
        """Deletes a show.

        Options:

        - **name**: name of the show to delete
        """
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
    def handle_stop(self):
        self.stop()
    handle_quit = handle_stop

    @debuglog
    def handle_terminate(self):
        self.stop(graceful=False)

    @debuglog
    def handle_numflies(self):
        return str(self.numflies())

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
    def handle_add_show(self, name, cmd):
        self.add_show(name, cmd)
        return "ok"

    @debuglog
    def handle_del_show(self, name):
        self.del_show(name)
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
