import time
import os
import functools

from circus.stats.collector import SocketStatsCollector
from circus.tests.support import TestCircus
from circus._zmq import ioloop
from circus.stats.streamer import StatsStreamer
from circus import util


TRAVIS = os.getenv('TRAVIS', False)


class _StatsStreamer(StatsStreamer):

    msgs = []

    def handle_recv(self, data):
        self.msgs.append(data)
        super(_StatsStreamer, self).handle_recv(data)


class TestStatsStreamer(TestCircus):

    def test_socketstats(self):
        if TRAVIS:
            return

        dummy_process = 'circus.tests.support.run_process'
        self.test_file = self._run_circus(dummy_process)
        endpoint = util.DEFAULT_ENDPOINT_DEALER
        pubsub = util.DEFAULT_ENDPOINT_SUB
        statspoint = util.DEFAULT_ENDPOINT_STATS

        loop = ioloop.IOLoop.instance()
        streamer = _StatsStreamer(endpoint, pubsub, statspoint,
                                  loop=loop)

        # now the stats collector
        self._collector = SocketStatsCollector(streamer, 'sockets',
                                               callback_time=0.1,
                                               io_loop=loop)

        self._collector.start()
        loop.add_callback(streamer._init)

        def _stop():
            streamer.stop()
            self._collector.stop()
            loop.stop()

        stopper = ioloop.DelayedCallback(_stop, 500, loop)
        stopper.start()
        loop.start()
        # let's see what we got
        self.assertTrue(len(streamer.msgs) > 1)
