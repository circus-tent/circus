import os
import warnings

from circus.tests.support import TestCircus, poll_for, Process, run_plugin
from circus.plugins.resource_watcher import ResourceWatcher


class Leaky(Process):
    def run(self):
        self._write('START')
        m = ' '
        while self.alive:
            m += '***' * 10000  # for memory

        self._write('STOP')


def run_leaky(test_file):
    process = Leaky(test_file)
    process.run()
    return 1


class TestResourceWatcher(TestCircus):

    @classmethod
    def setUpClass(cls):
        dummy_process = 'circus.tests.test_plugin_resource_watcher.run_leaky'
        cls.file, cls.arbiter = cls._create_circus(dummy_process)
        poll_for(cls.file, 'START')

    @classmethod
    def tearDownClass(cls):
        cls.arbiter.stop()
        if os.path.exists(cls.file):
            os.remove(cls.file)

    def _check_statsd(self, statsd, name):
        res = statsd.increments.items()
        self.assertTrue(len(res) > 0)
        for stat, items in res:
            if name == stat and items > 0:
                return
        raise AssertionError("%r stat not found" % name)

    def test_resource_watcher_max_mem(self):
        config = {'loop_rate': 0.1, 'max_mem': 0.05}

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

        self._check_statsd(_statsd, '_resource_watcher.test.over_memory')

        # Test that watcher is ok and not deprecated
        config['watcher'] = config['service']
        del config['service']

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == numws - 1

    def test_resource_watcher_min_mem(self):
        config = {'loop_rate': 0.1, 'min_mem': 100000.1}

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

        self._check_statsd(_statsd, '_resource_watcher.test.under_memory')

        # Test that watcher is ok and not deprecated
        config['watcher'] = config['service']
        del config['service']

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == numws - 1

    def test_resource_watcher_max_cpu(self):
        config = {'loop_rate': 0.1, 'max_cpu': 0.1}

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

        self._check_statsd(_statsd, '_resource_watcher.test.over_cpu')

        # Test that watcher is ok and not deprecated
        config['watcher'] = config['service']
        del config['service']

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == numws - 1

    def test_resource_watcher_min_cpu(self):
        config = {'loop_rate': 0.1, 'min_cpu': 30.0}

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

        self._check_statsd(_statsd, '_resource_watcher.test.under_cpu')

        # Test that watcher is ok and not deprecated
        config['watcher'] = config['service']
        del config['service']

        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            _statsd = run_plugin(ResourceWatcher, config)
            assert len(w) == numws - 1
