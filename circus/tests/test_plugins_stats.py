import unittest

from circus._zmq import ioloop
from circus.plugins.statsd import FullStats
from circus.tests.support import TestCircus, poll_for
from circus.util import DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB


class TestFullStats(TestCircus):
    def setUp(self):
        super(TestFullStats, self).setUp()
        dummy_process = 'circus.tests.support.run_process'
        self.test_file = self._run_circus(dummy_process)
        poll_for(self.test_file, 'START')


    def test_stat(self):
        config = {'loop_rate': 0.2}
        endpoint = DEFAULT_ENDPOINT_DEALER
        pubsub_endpoint = DEFAULT_ENDPOINT_SUB
        check_delay = 1
        ssh_server = None

        class _Statsd(object):
            gauges = []

            def gauge(self, name, value):
                self.gauges.append((name, value))

        _statsd = _Statsd()
        plugin = FullStats(endpoint, pubsub_endpoint, check_delay, ssh_server,
                           **config)
        plugin.statsd = _statsd

        # stops after 300 ms
        end = ioloop.DelayedCallback(plugin.loop.stop, 300, plugin.loop)
        end.start()
        plugin.start()

        # we should have a bunch of stats events here
        self.assertTrue(len(_statsd.gauges) >= 5)
        last_batch = [name for name, value in _statsd.gauges[-5:]]
        last_batch.sort()
        wanted = ['_stats.test.cpu_max', '_stats.test.cpu_sum',
                  '_stats.test.mem_max', '_stats.test.mem_sum',
                  '_stats.test.watchers_num']
        self.assertEqual(last_batch, wanted)
