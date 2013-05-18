from collections import defaultdict

from circus._zmq import ioloop
from circus.tests.support import TestCircus, poll_for, Process
from circus.util import DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB

from circus.plugins.statsd import FullStats
from circus.plugins.resource_watcher import ResourceWatcher


class Leaky(Process):
    def run(self):
        self._write('START')
        m = ' '
        while self.alive:
            m += '***' * 10000
        self._write('STOP')


def run_leaky(test_file):
    process = Leaky(test_file)
    process.run()
    return 1


class TestFullStats(TestCircus):
    def setUp(self):
        super(TestFullStats, self).setUp()
        dummy_process = 'circus.tests.test_plugins_stats.run_leaky'
        self.test_file = self._run_circus(dummy_process)
        poll_for(self.test_file, 'START')

    def _test_plugin(self, klass, config, duration=300):
        endpoint = DEFAULT_ENDPOINT_DEALER
        pubsub_endpoint = DEFAULT_ENDPOINT_SUB
        check_delay = 1
        ssh_server = None

        class _Statsd(object):
            gauges = []
            increments = defaultdict(int)

            def gauge(self, name, value):
                self.gauges.append((name, value))

            def increment(self, name):
                self.increments[name] += 1

        _statsd = _Statsd()
        plugin = klass(endpoint, pubsub_endpoint, check_delay, ssh_server,
                       **config)
        plugin.statsd = _statsd

        end = ioloop.DelayedCallback(plugin.loop.stop, duration, plugin.loop)
        end.start()
        plugin.start()
        return _statsd

    def test_full_stats(self):
        config = {'loop_rate': 0.2}
        _statsd = self._test_plugin(FullStats, config, 1000)

        # we should have a bunch of stats events here
        self.assertTrue(len(_statsd.gauges) >= 5)
        last_batch = [name for name, value in _statsd.gauges[-5:]]
        last_batch.sort()
        wanted = ['_stats.test.cpu_max', '_stats.test.cpu_sum',
                  '_stats.test.mem_max', '_stats.test.mem_sum',
                  '_stats.test.watchers_num']
        self.assertEqual(last_batch, wanted)

    def test_resource_watcher(self):
        config = {'loop_rate': 0.2, 'max_mem': 0.1}
        self.assertRaises(NotImplementedError, self._test_plugin,
                          ResourceWatcher, config)
        config['service'] = 'test'

        _statsd = self._test_plugin(ResourceWatcher, config)
        res = _statsd.increments.items()
        self.assertEqual(res, [('_resource_watcher.test.over_memory', 1)])
