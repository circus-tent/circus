from circus.tests.support import TestCircus, poll_for, Process, run_plugin
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


class TestResourceWatcher(TestCircus):
    def setUp(self):
        super(TestResourceWatcher, self).setUp()
        dummy_process = 'circus.tests.test_plugin_resource_watcher.run_leaky'
        self.test_file = self._run_circus(dummy_process)
        poll_for(self.test_file, 'START')

    def test_resource_watcher(self):
        config = {'loop_rate': 0.2, 'max_mem': 0.1}
        self.assertRaises(NotImplementedError, run_plugin,
                          ResourceWatcher, config)
        config['service'] = 'test'

        _statsd = run_plugin(ResourceWatcher, config)
        res = _statsd.increments.items()
        self.assertEqual(res, [('_resource_watcher.test.over_memory', 1)])

        # XXX need to cover cpu, health etc
