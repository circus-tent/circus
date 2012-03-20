import errno
import logging
import os

import zmq
from zmq.eventloop import ioloop

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus.flapping import Flapping
from circus import logger
from circus.watcher import Watcher
from circus.util import debuglog


class Arbiter(object):
    """Class used to control a list of watchers.

    Options:

    - **watchers**: a list of Watcher objects
    - **endpoint**: the controller ZMQ endpoint
    - **pubsub_endpoint**: the pubsub endpoint
    - **check_delay**: the delay between two controller points (default: 1 s)
    - **prereload_fn**: callable that will be executed on each reload
      (default: None)
    """
    def __init__(self, watchers, endpoint, pubsub_endpoint, check_delay=1.,
                 prereload_fn=None, context=None, loop=None,
                 check_flapping=True):
        self.watchers = watchers
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.prereload_fn = prereload_fn
        self.pubsub_endpoint = pubsub_endpoint

        # initialize zmq context
        self.context = context or zmq.Context.instance()
        self.loop = loop or ioloop.IOLoop()
        self.ctrl = Controller(endpoint, self.context, self.loop, self,
                check_delay)

        self.pid = os.getpid()
        self._watchers_names = {}
        self.alive = True
        self.busy = False
        self.check_flapping = check_flapping

    @debuglog
    def initialize(self):
        # event pub socket
        self.evpub_socket = self.context.socket(zmq.PUB)
        self.evpub_socket.bind(self.pubsub_endpoint)
        self.evpub_socket.linger = 0

        # initialize flapping
        if self.check_flapping:
            self.flapping = Flapping(self.context, self.endpoint,
                                     self.pubsub_endpoint, self.check_delay)

        # initialize watchers
        for watcher in self.watchers:
            self._watchers_names[watcher.name.lower()] = watcher
            watcher.initialize(self.evpub_socket)

    @debuglog
    def start(self):
        """Starts all the watchers.

        The start command is an infinite loop that waits
        for any command from a client and that watches all the
        processes and restarts them if needed.
        """
        logger.info("Starting master on pid %s" % self.pid)

        self.initialize()

        # start controller
        self.ctrl.start()

        # start flapping
        if self.check_flapping:
            logger.debug('Starting flapping')
            self.flapping.start()

        # initialize processes
        logger.debug('Initializing watchers')
        for watcher in self.watchers:
            watcher.manage_processes()

        logger.debug('Arbiter now waiting for commands')
        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
            else:
                break

        if self.check_flapping:
            self.flapping.stop()

        self.ctrl.stop()
        self.evpub_socket.close()

    def stop(self, graceful=False, destroy_context=True):
        if self.alive:
            self.stop_watchers(graceful=graceful, stop_alive=True)
        self.loop.stop()

    def manage_watchers(self):
        if not self.busy and self.alive:
            self.busy = True
            # manage and reap processes
            for watcher in self.watchers:
                watcher.reap_processes()
                watcher.manage_processes()

            if self.check_flapping and not self.flapping.is_alive():
                self.flapping = Flapping(self.context, self.endpoint,
                                         self.pubsub_endpoint,
                                         self.check_delay)
                self.flapping.start()

            self.busy = False

    @debuglog
    def reload(self, graceful=True):
        """Reloads everything.

        Run the :func:`prereload_fn` callable if any, then gracefuly
        reload all watchers.
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

        # gracefully reload watchers
        for watcher in self.watchers:
            watcher.reload(graceful=graceful)

    def numprocesses(self):
        """Return the number of processes running across all watchers."""
        return sum([len(watcher) for watcher in self.watchers])

    def numwatchers(self):
        """Return the number of watchers."""
        return len(self.watchers)

    def get_watcher(self, name):
        """Return the watcher *name*."""
        return self._watchers_names[name]

    def statuses(self):
        return dict([(watcher.name, watcher.status())
                      for watcher in self.watchers])

    def add_watcher(self, name, cmd):
        """Adds a watcher.

        Options:

        - **name**: name of the watcher to add
        - **cmd**: command to run.
        """
        if name in self._watchers_names:
            raise AlreadyExist("%r already exist" % name)

        if not name:
            return ValueError("command name shouldn't be empty")

        watcher = Watcher(name, cmd, stopped=True)
        watcher.initialize(self.evpub_socket)
        self.watchers.append(watcher)
        self._watchers_names[watcher.name.lower()] = watcher

    def rm_watcher(self, name):
        """Deletes a watcher.

        Options:

        - **name**: name of the watcher to delete
        """
        logger.debug('Deleting %r watcher' % name)

        # remove the watcher from the list
        watcher = self._watchers_names.pop(name)
        del self.watchers[self.watchers.index(watcher)]

        # stop the watcher
        watcher.stop()

    def start_watchers(self):
        for watcher in self.watchers:
            watcher.start()

    def stop_watchers(self, graceful=True, stop_alive=False):
        if stop_alive:
            if not self.alive:
                return

            self.alive = False

        for watcher in self.watchers:
            watcher.stop(graceful=graceful)
