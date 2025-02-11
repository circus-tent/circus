import socket
import time
from collections import defaultdict
from circus.fixed_threading import Thread

from tornado import ioloop

from circus.stats import collector as collector_module
from circus.stats.collector import SocketStatsCollector, WatcherStatsCollector
from circus.tests.support import TestCase, EasyTestSuite


class TestCollector(TestCase):

    def setUp(self):
        # let's create 10 sockets and their clients
        self.socks = []
        self.clients = []
        self.fds = []
        self.pids = {}

    def tearDown(self):
        for sock, _, _ in self.socks:
            sock.close()

        for sock in self.clients:
            sock.close()

    def _get_streamer(self):
        for i in range(10):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', 0))
            sock.listen(1)
            self.socks.append((sock, 'localhost:0', sock.fileno()))
            self.fds.append(sock.fileno())
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(sock.getsockname())
            self.clients.append(client)

        class FakeStreamer(object):
            stats = []

            def __init__(this):
                this.sockets = self.socks

            @property
            def circus_pids(this):
                return self.circus_pids

            def get_pids(this, name):
                return self.pids[name]

            @property
            def publisher(this):
                return this

            def publish(this, name, stat):
                this.stats.append(stat)

        self.streamer = FakeStreamer()
        return self.streamer

    def _get_collector(self, collector_class):
        self._get_streamer()

        class Collector(Thread):

            def __init__(this, streamer):
                Thread.__init__(this)
                this.streamer = streamer
                this.loop = ioloop.IOLoop()
                this.daemon = True

            def run(self):
                self.loop.make_current()
                collector = collector_class(
                    self.streamer, 'sockets', callback_time=0.1,
                    io_loop=self.loop)
                collector.start()
                self.loop.start()

            def stop(self):
                self.loop.add_callback(self.loop.stop)
                self.loop.add_callback(self.loop.close)

        return Collector(self.streamer)

    def test_watcherstats(self):
        calls = defaultdict(int)
        info = []
        for i in range(2):
            info.append({
                'age': 154058.91111397743 + i,
                'children': [],
                'cmdline': 'python',
                'cpu': 0.0 + i / 10.,
                'create_time': 1378663281.96,
                'ctime': '0:00.0',
                'mem': 0.0,
                'mem_info1': '52K',
                'mem_info2': '39M',
                'nice': 0,
                'pid': None,
                'username': 'alexis'})

        def _get_info(pid):
            try:
                data = info[calls[pid]].copy()
            except IndexError:
                raise collector_module.util.NoSuchProcess(pid)
            data['pid'] = pid
            calls[pid] += 1
            return data

        old_info = collector_module.util.get_info
        try:
            collector_module.util.get_info = _get_info

            self.pids['firefox'] = [2353, 2354]
            collector = WatcherStatsCollector(self._get_streamer(), 'firefox')

            stats = list(collector.collect_stats())
            self.assertEqual(len(stats), 3)

            stats = list(collector.collect_stats())
            self.assertEqual(len(stats), 3)

            stats = list(collector.collect_stats())
            self.assertEqual(len(stats), 1)

            self.circus_pids = {1234: 'ohyeah'}
            self.pids['circus'] = [1234]
            collector = WatcherStatsCollector(self._get_streamer(), 'circus')
            stats = list(collector.collect_stats())
            self.assertEqual(stats[0]['name'], 'ohyeah')

        finally:
            collector_module.util.get_info = old_info

    def test_collector_aggregation(self):
        collector = WatcherStatsCollector(self._get_streamer(), 'firefox')
        aggregate = {}
        for i in range(0, 10):
            pid = 1000 + i
            aggregate[pid] = {
                'age': 154058.91111397743, 'children': [],
                'cmdline': 'python', 'cpu': 0.0 + i / 10.,
                'create_time': 1378663281.96,
                'ctime': '0:00.0', 'mem': 0.0 + i // 10,
                'mem_info1': '52K', 'mem_info2': '39M',
                'username': 'alexis', 'subtopic': pid, 'name': 'firefox'}

        res = collector._aggregate(aggregate)
        self.assertEqual(res['mem'], 0)
        self.assertEqual(len(res['pid']), 10)
        self.assertEqual(res['cpu'], 0.45)

    def test_collector_aggregation_when_unknown_values(self):
        collector = WatcherStatsCollector(self._get_streamer(), 'firefox')
        aggregate = {}
        for i in range(0, 10):
            pid = 1000 + i
            aggregate[pid] = {
                'age': 'N/A', 'children': [], 'cmdline': 'python',
                'cpu': 'N/A', 'create_time': 1378663281.96,
                'ctime': '0:00.0', 'mem': 'N/A', 'mem_info1': '52K',
                'mem_info2': '39M', 'nice': 0, 'pid': pid,
                'username': 'alexis', 'subtopic': pid, 'name': 'firefox'}

        res = collector._aggregate(aggregate)
        self.assertEqual(res['mem'], 'N/A')
        self.assertEqual(len(res['pid']), 10)
        self.assertEqual(res['cpu'], 'N/A')

    def test_socketstats(self):
        collector = self._get_collector(SocketStatsCollector)
        collector.start()
        time.sleep(1.)

        # doing some socket things as a client
        for i in range(10):
            for client in self.clients:
                client.send(b'ok')
                # client.recv(2)

        # stopping
        collector.stop()
        for s, _, _ in self.socks:
            s.close()

        # let's see what we got
        self.assertTrue(len(self.streamer.stats) > 2)

        stat = self.streamer.stats[0]
        self.assertTrue(stat['fd'] in self.fds)
        self.assertTrue(stat['reads'] > 1)


test_suite = EasyTestSuite(__name__)
