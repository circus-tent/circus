from collections import deque
import errno
import logging
import os
import sys
import time
from functools import wraps

import zmq
from zmq.eventloop import ioloop, zmqstream

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
                 prereload_fn=None, context=None, loop=None):
        self.shows = shows
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.prereload_fn = prereload_fn
        self.pubsub_endpoint = pubsub_endpoint
        self.context = context or zmq.Context()
        self.loop = loop or ioloop.IOLoop()

        self.pid = os.getpid()
        self._shows_names = {}
        self.alive = True
        self.initialize()

        self.busy = False

    def initialize(self):
        # event pub socket
        self.evpub_socket  = self.context.socket(zmq.PUB)
        self.evpub_socket.bind(self.pubsub_endpoint)

        # initialize controller
        ctrl_socket = self.context.socket(zmq.ROUTER)
        ctrl_socket.bind(self.endpoint)
        self.ctrl = Controller(zmqstream.ZMQStream(ctrl_socket, self.loop),
                               self.loop, self, self.check_delay)

        # initialize flapping
        self.flapping = Flapping(self.endpoint, self.pubsub_endpoint,
                self.check_delay)

        # initialize shows
        for show in self.shows:
            self._shows_names[show.name.lower()] = show
            show.initialize(self.evpub_socket)


    @debuglog
    def start(self):
        """Starts all the shows.

        The start command is an infinite loop that waits
        for any command from a client and that watches all the
        flies and restarts them if needed.
        """

        logger.info("Starting master on pid %s" % self.pid)

        # start controller
        self.ctrl.start()

        # start flapping
        self.flapping.start()

        # initialize flies
        for show in self.shows:
            show.manage_flies()

        while self.alive:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
            else:
                break

    def manage_shows(self):
        if not self.busy and self.alive:
            self.busy = True
            # manage and reap flies
            for show in self.shows:
                show.reap_flies()
                show.manage_flies()

            if not self.flapping.is_alive():
                self.start_flapping()

            self.busy = False


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

        self.ctrl.stop()

    def terminate(self, destroy_context=True):
        if self.alive:
            self.stop(graceful=False)

        time.sleep(0.1)
        self.loop.stop()

        if self.context is not None and destroy_context:
            if not self.context.closed:
                self.context.destroy(0)
            self.context = None

    @debuglog
    def reload(self, graceful=True):
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
            show.reload(graceful=graceful)

    def numflies(self):
        """Return the number of flies running across all shows."""
        return sum([len(show) for show in self.shows])

    def numshows(self):
        """Return the number of shows."""
        return len(self.shows)

    def get_show(self, name):
        """Return the show *name*."""
        return self._shows_names[name]

    def statuses(self):
        statuses = ["%s: %s" % (show.name, show.status()) for show in self.shows]
        return "\n".join(statuses)

    def add_show(self, name, cmd):
        """Adds a show.

        Options:

        - **name**: name of the show to add
        - **cmd**: command to run.
        """
        if name in self._shows_names:
            raise AlreadyExist("%r already exist" % show.name)

        show = Show(name, cmd, stopped=True)
        show.initialize(self.evpub_socket)
        self.shows.append(show)
        self._shows_names[show.name.lower()] = show

    def rm_show(self, name):
        """Deletes a show.

        Options:

        - **name**: name of the show to delete
        """
        logger.debug('Deleting %r show' % name)

        # remove the show from the list
        show = self._shows_names.pop(name)
        del self.shows[self.shows.index(show)]

        # stop the show
        show.stop()

    def start_shows(self):
        for show in self.shows:
            show.start()

    def stop_shows(self, graceful=True):
        for show in self.shows:
            show.stop(graceful=graceful)
