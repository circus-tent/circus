import zmq
import unittest
import time
import os
import Queue

from circus.stats.collector import StatsCollector
from circus.stats.publisher import StatsPublisher
from circus.stats import publisher


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

    closed = False
    data = []

    def bind(self, *args):
        pass

    def send_multipart(self, data):
        self.data.append(data)


class Context(object):
    socket = Socket

    def destroy(self, *args):
        pass


class FakeZMQ(object):
    Context = Context
    PUB = None
    ZMQError = zmq.ZMQError


class TestStats(unittest.TestCase):
    def setUp(self):
        self._ctx = zmq.Context
        self._p = publisher.zmq
        publisher.zmq = zmq.context = FakeZMQ

    def tearDown(self):
        zmq.context = self._ctx
        publisher.zmq = self._p

    def test_collector(self):
        streamer = FakeStreamer()

        collector = StatsCollector(streamer)

        collector.start()

        while streamer.results.qsize() < 10:
            time.sleep(.1)

        collector.stop()

        # what do we have
        res = [streamer.results.get() for e in range(9)]
        self.assertEqual(res[0][3]['pid'], os.getpid())

    def test_publisher(self):
        streamer = FakeStreamer()
        streamer.results.put(['watcher', 'name', os.getpid(), {}])

        pub = StatsPublisher(streamer, stats_endpoint='xxx')
        pub.start()

        time.sleep(1.)
        pub.stop()

        topics = [data[0] for data in pub.socket.data]
        self.assertTrue('stat.watcher.%d' % os.getpid() in topics)
