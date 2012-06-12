import threading
import json
import unittest
import time
import os
import Queue

import zmq

from circus.stats.collector import StatsCollector
from circus.stats.streamer import StatsStreamer
from circus.stats.publisher import StatsPublisher
from circus.stats import publisher, streamer
from circus import client


class FakeStreamer(object):
    results = Queue.Queue()

    def get_watchers(self):
        return ['one', 'two']

    def get_pids(self, watcher):
        return [os.getpid()]

    def get_circus_pids(self):
        return [('proc', os.getpid())]


class Socket(object):
    def __init__(self, *args, **kw):
        pass

    closed = bind_to_random_port = False
    data = []

    def fileno(self):
        return 0

    def recv(self):
        return json.dumps({'watchers': ['watcher'],
                           'pids': [os.getpid()],
                           'info': {'pid': os.getpid()}})

    def bind(self, *args):
        pass

    connect = setsockopt = setsockopt_unicode = getsockopt = bind
    send = getsockopt_unicode = bind

    def send_multipart(self, data):
        self.data.append(data)


class Context(object):
    socket = Socket

    def destroy(self, *args):
        pass


class Poller(object):
    def register(self, *args):
        pass

    def poll(self, *args):
        return {Socket(): 'xx'}


class FakeZMQ(object):
    Context = Context
    DEALER = IDENTITY = LINGER = SUBSCRIBE = PUB = SUB = None
    ZMQError = zmq.ZMQError
    Poller = Poller
    POLLIN = None


class TestStats(unittest.TestCase):
    def setUp(self):
        self._ctx = zmq.Context
        self._p = publisher.zmq
        self._s = streamer.zmq
        self._c = client.zmq
        publisher.zmq = streamer.zmq = zmq.context = FakeZMQ
        client.zmq = FakeZMQ

    def tearDown(self):
        zmq.context = self._ctx
        publisher.zmq = self._p
        streamer.zmq = self._s
        client.zmq = self._c

    def _test_collector(self):
        streamer = FakeStreamer()

        collector = StatsCollector(streamer)

        collector.start()

        while streamer.results.qsize() < 10:
            time.sleep(.1)

        collector.stop()

        # what do we have
        res = [streamer.results.get() for e in range(9)]
        self.assertEqual(res[0][3]['pid'], os.getpid())

    def _test_publisher(self):
        streamer = FakeStreamer()
        streamer.results.put(['watcher', 'name', os.getpid(), {}])

        pub = StatsPublisher(streamer, stats_endpoint='xxx')
        pub.start()

        time.sleep(1.)
        pub.stop()

        topics = [data[0] for data in pub.socket.data]
        self.assertTrue('stat.watcher.%d' % os.getpid() in topics)

    def _test_streamer(self):

        class ThreadedStream(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.daemon = True

            def run(self):
                self.s = streamer = StatsStreamer('endpoint', 'pub', 'stats')
                streamer.start()

            def stop(self):
                self.s.stop()

        th = ThreadedStream()
        th.start()
        time.sleep(1.)
        th.stop()

        self.assertTrue(len(th.s.publisher.socket.data) > 3)
