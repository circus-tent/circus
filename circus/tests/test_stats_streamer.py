import os
import json
import tempfile

from circus.stats.collector import SocketStatsCollector
from circus.tests.support import TestCircus
from circus._zmq import ioloop
from circus.stats.streamer import StatsStreamer
from circus import util
from circus import client


TRAVIS = os.getenv('TRAVIS', False)


class _StatsStreamer(StatsStreamer):

    msgs = []

    def handle_recv(self, data):
        self.msgs.append(data)
        super(_StatsStreamer, self).handle_recv(data)


class TestStatsStreamer(TestCircus):

    def setUp(self):
        self.old = client.CircusClient.call
        client.CircusClient.call = self._call
        fd, self._unix = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        client.CircusClient.call = self.old
        os.remove(self._unix)

    def _call(self, cmd):
        what = cmd['command']
        if what == 'list':
            name = cmd['properties'].get('name')
            if name is None:
                return {'watchers': ['one', 'two', 'three']}
            return {'pids': [123, 456]}
        elif what == 'dstats':
            return {'info': {'pid': 789}}
        elif what == 'listsockets':
            return {'status': u'ok',
                    'sockets': [{'path': self._unix,
                                'fd': 5,
                                'name': u'XXXX',
                                'backlog': 2048}],
                    'time': 1369647058.967524}

        raise NotImplementedError(cmd)

    def test_socketstats(self):
        if TRAVIS:
            return

        endpoint = util.DEFAULT_ENDPOINT_DEALER
        pubsub = util.DEFAULT_ENDPOINT_SUB
        statspoint = util.DEFAULT_ENDPOINT_STATS

        loop = ioloop.IOLoop()
        streamer = _StatsStreamer(endpoint, pubsub, statspoint,
                                  loop=loop)

        # now the stats collector
        self._collector = SocketStatsCollector(streamer, 'sockets',
                                               callback_time=0.1,
                                               io_loop=loop)

        self._collector.start()
        loop.add_callback(streamer._init)

        # events
        def _events():
            msg = 'one.spawn', json.dumps({'process_pid': 187})
            for i in range(5):
                streamer.handle_recv(msg)

        events = ioloop.DelayedCallback(_events, 500, loop)
        events.start()

        def _stop():
            self._collector.stop()
            streamer.stop()

        stopper = ioloop.DelayedCallback(_stop, 500, loop)
        stopper.start()
        streamer.start()

        # let's see what we got
        try:
            self.assertTrue(len(streamer.msgs) > 1)
        finally:
            streamer.stop()
