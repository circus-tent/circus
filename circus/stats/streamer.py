from collections import defaultdict
import zmq
import json
import threading
import Queue

from circus.consumer import CircusConsumer
from circus.commands import get_commands
from circus.client import CircusClient
from circus.stats.collector import StatsCollector
from circus.stats.publisher import StatsPublisher
from circus import logger


class StatsStreamer(object):
    def __init__(self, endpoint, pubsub_endoint, stats_endpoint, pool_size=10):
        self.topic = 'watcher.'
        self.ctx = zmq.Context()
        self.consumer = CircusConsumer([self.topic], context=self.ctx,
                                       endpoint=pubsub_endoint)
        self.client = CircusClient(context=self.ctx, endpoint=endpoint)
        self.cmds = get_commands()
        self.watchers = defaultdict(list)
        self._pids = []
        self.running = False
        self.stopped = False
        self.lock = threading.RLock()
        self.results = Queue.Queue()
        self.stats = StatsCollector(self, pool_size)
        self.publisher = StatsPublisher(self, stats_endpoint, context=self.ctx)

    def get_pids(self):
        return self._pids

    def _init(self):
        with self.lock:
            self.stopped = False
            self._pids = []
            # getting the initial list of watchers/pids
            msg = self.cmds['list'].make_message()
            res = self.client.call(msg)
            for watcher in res['watchers']:
                msg = self.cmds['listpids'].make_message(name=watcher)
                res = self.client.call(msg)
                for pid in res['pids']:
                    if pid in self._pids:
                        continue
                    self._pids.append(pid)

    def remove_pid(self, pid):
        logger.debug('Removing %d' % pid)
        if pid in self._pids:
            with self.lock:
                self._pids.remove(pid)

    def append_pid(self, pid):
        logger.debug('Adding %d' % pid)
        if pid in self._pids:
            return
        with self.lock:
            self._pids.append(pid)

    def start(self):
        logger.info('Starting the stats streamer')
        self._init()
        logger.debug('Initial list is ' + str(self._pids))
        self.running = True
        self.stats.start()
        self.publisher.start()

        while self.running:
            # now hooked into the stream
            try:
                for topic, msg in self.consumer:
                    __, name, action = topic.split('.')
                    msg = json.loads(msg)
                    if action != 'start' and self.stopped:
                        self._init()

                    if action in ('reap', 'kill'):
                        # a process was reaped
                        pid = msg['process_pid']
                        if pid in self._pids:
                            with self.lock:
                                self._pids.remove(pid)
                    elif action == 'spawn':
                        pid = msg['process_pid']
                        if pid not in self._pids:
                            with self.lock:
                                self._pids.append(pid)
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
