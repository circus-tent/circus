from collections import defaultdict
from itertools import chain
import os
import errno
import socket

import zmq
import zmq.utils.jsonapi as json
from tornado import ioloop
from zmq.eventloop import zmqstream

from circus.commands import get_commands
from circus.client import CircusClient
from circus.stats.collector import WatcherStatsCollector, SocketStatsCollector
from circus.stats.publisher import StatsPublisher
from circus import logger
from circus.util import to_str


class StatsStreamer(object):
    def __init__(self, endpoint, pubsub_endoint, stats_endpoint,
                 ssh_server=None, delay=1., loop=None):
        self.topic = b'watcher.'
        self.delay = delay
        self.ctx = zmq.Context()
        self.pubsub_endpoint = pubsub_endoint
        self.sub_socket = self.ctx.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, self.topic)
        self.sub_socket.connect(self.pubsub_endpoint)
        self.loop = loop or ioloop.IOLoop.current()
        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)
        self.client = CircusClient(context=self.ctx, endpoint=endpoint,
                                   ssh_server=ssh_server)
        self.cmds = get_commands()
        self.publisher = StatsPublisher(stats_endpoint, self.ctx)
        self._initialize()

    def _initialize(self):
        self._pids = defaultdict(list)
        self._callbacks = dict()
        self.running = False  # should the streamer be running?
        self.stopped = False  # did the collect started yet?
        self.circus_pids = {}
        self.sockets = []
        self.get_watchers = self._pids.keys

    def get_pids(self, watcher=None):
        if watcher is not None:
            if watcher == 'circus':
                return list(self.circus_pids.keys())
            return self._pids[watcher]
        return chain(*list(self._pids.values()))

    def get_circus_pids(self):
        watchers = self.client.send_message('list').get('watchers', [])

        # getting the circusd, circusd-stats and circushttpd pids
        res = self.client.send_message('dstats')
        pids = {os.getpid(): 'circusd-stats'}

        if 'info' in res:
            pids[res['info']['pid']] = 'circusd'

        if 'circushttpd' in watchers:
            httpd_pids = self.client.send_message('list', name='circushttpd')

            if 'pids' in httpd_pids:
                httpd_pids = httpd_pids['pids']
                if len(httpd_pids) == 1:
                    pids[httpd_pids[0]] = 'circushttpd'

        return pids

    def _add_callback(self, name, start=True, kind='watcher'):
        logger.debug('Callback added for %s' % name)

        if kind == 'watcher':
            klass = WatcherStatsCollector
        elif kind == 'socket':
            klass = SocketStatsCollector
        else:
            raise ValueError('Unknown callback kind %r' % kind)

        self._callbacks[name] = klass(self, name, self.delay, self.loop)
        if start:
            self._callbacks[name].start()

    def _init(self):
        self._pids.clear()

        # getting the initial list of watchers/pids
        res = self.client.send_message('list')

        for watcher in res['watchers']:
            if watcher in ('circusd', 'circushttpd', 'circusd-stats'):
                # this is dealt by the special 'circus' collector
                continue

            pid_list = self.client.send_message('list', name=watcher)
            pids = pid_list.get('pids', [])
            for pid in pids:
                self._append_pid(watcher, pid)

        # getting the circus pids
        self.circus_pids = self.get_circus_pids()
        if 'circus' not in self._callbacks:
            self._add_callback('circus')
        else:
            self._callbacks['circus'].start()

        # getting the initial list of sockets
        res = self.client.send_message('listsockets')
        for sock in res.get('sockets', []):
            fd = sock['fd']
            if 'path' in sock:
                # unix socket
                address = sock['path']
            else:
                address = '%s:%s' % (sock['host'], sock['port'])

            # XXX type / family ?
            sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
            self.sockets.append((sock, address, fd))

        self._add_callback('sockets', kind='socket')

    def stop_watcher(self, watcher):
        for pid in self._pids[watcher]:
            self.remove_pid(watcher, pid)

    def remove_pid(self, watcher, pid):
        if pid in self._pids[watcher]:
            logger.debug('Removing %d from %s' % (pid, watcher))
            self._pids[watcher].remove(pid)
            if len(self._pids[watcher]) == 0:
                logger.debug(
                    'Stopping the periodic callback for {0}' .format(watcher))
                self._callbacks[watcher].stop()

    def _append_pid(self, watcher, pid):
        if watcher not in self._pids or len(self._pids[watcher]) == 0:
            logger.debug(
                'Starting the periodic callback for {0}'.format(watcher))
            if watcher not in self._callbacks:
                self._add_callback(watcher)
            else:
                self._callbacks[watcher].start()

        if pid in self._pids[watcher]:
            return
        self._pids[watcher].append(pid)
        logger.debug('Adding %d in %s' % (pid, watcher))

    def start(self):
        self.running = True
        logger.info('Starting the stats streamer')
        self._init()
        logger.debug('Initial list is ' + str(self._pids))
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
        self.stop()

    def handle_recv(self, data):
        """called each time circusd sends an event"""
        # maintains a periodic callback to compute mem and cpu consumption for
        # each pid.
        logger.debug('Received an event from circusd: %s' % str(data))
        topic, msg = data
        try:
            topic = to_str(topic)
            watcher = topic.split('.')[1:-1][0]
            action = topic.split('.')[-1]
            msg = json.loads(msg)

            if action in ('reap', 'kill'):
                # a process was reaped
                pid = msg['process_pid']
                self.remove_pid(watcher, pid)
            elif action == 'spawn':
                # a process was added
                pid = msg['process_pid']
                self._append_pid(watcher, pid)
            elif action == 'stop':
                # the whole watcher was stopped.
                self.stop_watcher(watcher)
            else:
                logger.debug('Unknown action: %r' % action)
                logger.debug(msg)
        except Exception:
            logger.exception('Failed to handle %r' % msg)

    def stop(self):
        # stop all the periodic callbacks running
        for callback in self._callbacks.values():
            callback.stop()

        self.loop.stop()
        self.ctx.destroy(0)
        self.publisher.stop()
        self.stopped = True
        self.running = False
        logger.info('Stats streamer stopped')
