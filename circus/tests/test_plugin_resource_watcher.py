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
        found = False

        with warnings.catch_warnings(record=True) as ws:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            numws = len(ws)
            for w in ws:
                if not found:
                    found = 'ResourceWatcher' in str(w.message)

        if not found:
            raise AssertionError('ResourceWatcher not found')

        res = _statsd.increments.items()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], '_resource_watcher.test.over_memory')
        self.assertTrue(res[0][1] > 0)

        # Test that watcher is ok and not deprecated
        config['watcher'] = config['service']
        del config['service']

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == numws - 1

        # XXX need to cover cpu, health etc
