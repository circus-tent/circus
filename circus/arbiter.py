import errno
import logging
import os
from threading import Thread, RLock
import time
import sys

import zmq
from zmq.eventloop import ioloop

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus import logger
from circus.watcher import Watcher
from circus.util import debuglog, _setproctitle
from circus.config import get_config

# will be imported by plugin registration later XXX
from circus.plugins.flapping import Flapping


class Arbiter(object):
    """Class used to control a list of watchers.

    Options:

    - **watchers** -- a list of Watcher objects
    - **endpoint** -- the controller ZMQ endpoint
    - **pubsub_endpoint** -- the pubsub endpoint
    - **stats_endpoint** -- the stats endpoint. If not provided,
      the *circusd-stats* process will not be launched.
    - **check_delay** -- the delay between two controller points
      (default: 1 s)
    - **prereload_fn** -- callable that will be executed on each reload
      (default: None)
    - **context** -- if provided, the zmq context to reuse.
      (default: None)
    - **loop**: if provided, a :class:`zmq.eventloop.ioloop.IOLoop` instance
       to reuse. (default: None)
    - **check_flapping** -- when True, Circus will check for flapping
      processes and automatically restart them. (default: True)
    """
    def __init__(self, watchers, endpoint, pubsub_endpoint, check_delay=1.,
                 prereload_fn=None, context=None, loop=None,
                 check_flapping=True, stats_endpoint=None):
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
        self._lock = RLock()
        self.check_flapping = check_flapping

        # initializing circusd-stats as a watcher when configured
        self.stats_endpoint = stats_endpoint
        if self.stats_endpoint is not None:
            cmd = "%s -c 'from circus import stats; stats.main()'" % \
                        sys.executable
            cmd += ' --endpoint %s' % self.endpoint
            cmd += ' --pubsub %s' % self.pubsub_endpoint
            cmd += ' --statspoint %s' % self.stats_endpoint
            stats_watcher = Watcher('circusd-stats', cmd)
            self.watchers.append(stats_watcher)

    @classmethod
    def load_from_config(cls, config_file):
        cfg = get_config(config_file)

        # hack reload ioloop to use the monkey patched version
        reload(ioloop)

        watchers = []
        for watcher in cfg.get('watchers', []):
            watchers.append(Watcher.load_from_config(watcher))

        # creating arbiter
        arbiter = cls(watchers, cfg['endpoint'], cfg['pubsub_endpoint'],
                      check_delay=cfg.get('check_delay', 1.),
                      prereload_fn=cfg.get('prereload_fn'),
                      stats_endpoint=cfg.get('stats_endpoint'))

        return arbiter

    def iter_watchers(self):
        watchers = [(watcher.priority, watcher) for watcher in self.watchers]
        watchers.sort()
        watchers.reverse()
        for __, watcher in watchers:
            yield watcher

    @debuglog
    def initialize(self):
        # set process title
        _setproctitle("circusd")

        # event pub socket
        self.evpub_socket = self.context.socket(zmq.PUB)
        self.evpub_socket.bind(self.pubsub_endpoint)
        self.evpub_socket.linger = 0

        # initialize flapping
        if self.check_flapping:
            self.flapping = Flapping(self.context, self.endpoint,
                                     self.pubsub_endpoint, self.check_delay)

        # initialize watchers
        for watcher in self.iter_watchers():
            self._watchers_names[watcher.name.lower()] = watcher
            watcher.initialize(self.evpub_socket)

    @debuglog
    def start(self):
        """Starts all the watchers.

        The start command is an infinite loop that waits
        for any command from a client and that watches all the
        processes and restarts them if needed.
        """
        logger.info("Starting master on pid %s", self.pid)

        self.initialize()

        # start controller
        self.ctrl.start()

        # start flapping
        if self.check_flapping:
            logger.debug('Starting flapping')
            self.flapping.start()

        # initialize processes
        logger.debug('Initializing watchers')
        for watcher in self.iter_watchers():
            watcher.start()

        logger.info('Arbiter now waiting for commands')
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

    def stop(self):
        if self.alive:
            self.stop_watchers(stop_alive=True)
        self.loop.stop()

    def reap_processes(self):
        # map watcher to pids
        watchers_pids = {}
        for watcher in self.iter_watchers():
            if not watcher.stopped:
                for pid, wid in watcher.pids.items():
                    watchers_pids[pid] = (watcher, wid)

        # detect dead children
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if not pid:
                    break

                if pid in watchers_pids:
                    watcher, wid = watchers_pids[pid]
                    watcher.reap_process(wid, status)
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    time.sleep(0.001)
                    continue
                elif e.errno == errno.ECHILD:
                    # process already reaped
                    return
                else:
                    raise

    def manage_watchers(self):
        if not self.alive:
            return

        with self._lock:
            # manage and reap processes
            self.reap_processes()
            for watcher in self.iter_watchers():
                watcher.manage_processes()

            if self.check_flapping and not self.flapping.is_alive():
                self.flapping = Flapping(self.context, self.endpoint,
                                            self.pubsub_endpoint,
                                            self.check_delay)
                self.flapping.start()

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
        for watcher in self.iter_watchers():
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

    def add_watcher(self, name, cmd, **kw):
        """Adds a watcher.

        Options:

        - **name**: name of the watcher to add
        - **cmd**: command to run.
        - all other options defined in the Watcher constructor.
        """
        if name in self._watchers_names:
            raise AlreadyExist("%r already exist" % name)

        if not name:
            return ValueError("command name shouldn't be empty")

        watcher = Watcher(name, cmd, **kw)
        watcher.initialize(self.evpub_socket)
        self.watchers.append(watcher)
        self._watchers_names[watcher.name.lower()] = watcher
        return watcher

    def rm_watcher(self, name):
        """Deletes a watcher.

        Options:

        - **name**: name of the watcher to delete
        """
        logger.debug('Deleting %r watcher', name)

        # remove the watcher from the list
        watcher = self._watchers_names.pop(name)
        del self.watchers[self.watchers.index(watcher)]

        # stop the watcher
        watcher.stop()

    def start_watchers(self):
        for watcher in self.iter_watchers():
            watcher.start()

    def stop_watchers(self, stop_alive=False):
        if not self.alive:
            return

        if stop_alive:
            logger.info('Arbiter exiting')
            self.alive = False

        for watcher in self.iter_watchers():
            watcher.stop()

    def restart(self):
        self.stop_watchers()
        self.start_watchers()


class ThreadedArbiter(Arbiter, Thread):

    def __init__(self, watchers, endpoint, pubsub_endpoint, check_delay=1.,
                 prereload_fn=None, context=None, loop=None,
                 check_flapping=True):
        Thread.__init__(self)
        Arbiter.__init__(self, watchers, endpoint, pubsub_endpoint,
                         check_delay, prereload_fn, context, loop,
                         check_flapping)

    def start(self):
        return Thread.start(self)

    def run(self):
        return Arbiter.start(self)

    def stop(self):
        Arbiter.stop(self)
        self.join()
