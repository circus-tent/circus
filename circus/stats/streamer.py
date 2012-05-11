from collections import defaultdict
import zmq
import json
import threading
import Queue
from itertools import chain
import os
import errno

from zmq.eventloop import ioloop, zmqstream

from circus.commands import get_commands
from circus.client import CircusClient
from circus.stats.collector import StatsCollector
from circus.stats.publisher import StatsPublisher
from circus import logger


class StatsStreamer(object):
    def __init__(self, endpoint, pubsub_endoint, stats_endpoint):
        self.topic = 'watcher.'
        self.ctx = zmq.Context()
        self.pubsub_endpoint = pubsub_endoint
        self.sub_socket = self.ctx.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, self.topic)
        self.sub_socket.connect(self.pubsub_endpoint)
        self.loop = ioloop.IOLoop()
        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)
        self.client = CircusClient(context=self.ctx, endpoint=endpoint)
        self.cmds = get_commands()
        self.watchers = defaultdict(list)
        self._pids = defaultdict(list)
        self.running = False
        self.stopped = False
        self.lock = threading.RLock()
        self.results = Queue.Queue()
        self.stats = StatsCollector(self)
        self.publisher = StatsPublisher(self, stats_endpoint, context=self.ctx)

    def get_watchers(self):
        return self._pids.keys()

    def get_pids(self, watcher=None):
        if watcher is not None:
            return self._pids[watcher]
        return chain(self._pid.values())

    def get_circus_pids(self):
        # getting the circusd pid
        msg = self.cmds['dstats'].make_message()
        res = self.client.call(msg)
        return [('circusd-stats', os.getpid()),
                ('circusd', res['info']['pid'])]

    def _init(self):
        with self.lock:
            self.stopped = False
            self._pids.clear()
            # getting the initial list of watchers/pids
            msg = self.cmds['list'].make_message()
            res = self.client.call(msg)
            for watcher in res['watchers']:
                msg = self.cmds['listpids'].make_message(name=watcher)
                res = self.client.call(msg)
                for pid in res['pids']:
                    if pid in self._pids[watcher]:
                        continue
                    self._pids[watcher].append(pid)

    def remove_pid(self, watcher, pid):
        logger.debug('Removing %d from %s' % (pid, watcher))
        if pid in self._pids[watcher]:
            with self.lock:
                self._pids[watcher].remove(pid)

    def append_pid(self, watcher, pid):
        logger.debug('Adding %d in %s' % (pid, watcher))
        if pid in self._pids[watcher]:
            return
        with self.lock:
            self._pids[watcher].append(pid)

    def start(self):
        logger.info('Starting the stats streamer')
        self._init()
        logger.debug('Initial list is ' + str(self._pids))
        self.running = True
        self.stats.start()
        self.publisher.start()
        logger.debug('Now looping to get circusd events')

        while self.running:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                logger.debug(str(e))

                if e.errno == errno.EINTR:
                    continue
                elif e.errno == zmq.ETERM:
                    break
                else:
                    logger.debug("got an unexpected error %s (%s)", str(e),
                                 e.errno)
                    raise
            else:
                break

        self.sub_socket.close()

    def handle_recv(self, data):
        topic, msg = data
        try:
            __, watcher, action = topic.split('.')
            msg = json.loads(msg)
            if action != 'start' and self.stopped:
                self._init()
            if action in ('reap', 'kill'):
                # a process was reaped
                pid = msg['process_pid']
                self.remove_pid(watcher, pid)
            elif action == 'spawn':
                pid = msg['process_pid']
                self.append_pid(watcher, pid)
            elif action == 'start':
                self._init()
            elif action == 'stop':
                # nothing to do
                self.stopped = True
            else:
                logger.debug('Unknown action: %r' % action)
                logger.debug(msg)
        except Exception:
            logger.exception('Failed to treat %r' % msg)

    def stop(self):
        self.running = False
        self.publisher.stop()
        self.stats.stop()
        self.ctx.destroy(0)
        logger.info('Stats streamer stopped')
