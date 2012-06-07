import unittest
import time
import os
import Queue

from circus.stats.collector import StatsCollector


class FakeStreamer(object):
    results = Queue.Queue()

    def get_watchers(self):
        return ['one', 'two']

    def get_pids(self, watcher):
        return [os.getpid()]

    def get_circus_pids(self):
        return [('proc', os.getpid())]


class TestStatsCollector(unittest.TestCase):

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
