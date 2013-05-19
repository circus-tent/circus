import warnings
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

        # Test that service is deprecated
        config['service'] = 'test'

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "deprecated" in str(w[-1].message)

        res = _statsd.increments.items()
        self.assertEqual(res, [('_resource_watcher.test.over_memory', 1)])

        # Test that watcher is ok and not deprecated
        config['watcher'] = config['service']
        del config['service']

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == 0

        # XXX need to cover cpu, health etc
