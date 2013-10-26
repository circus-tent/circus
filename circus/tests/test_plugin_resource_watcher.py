import warnings

from tornado.testing import gen_test

from circus.tests.support import TestCircus, async_poll_for, Process
from circus.tests.support import async_run_plugin, EasyTestSuite
from circus.plugins.resource_watcher import ResourceWatcher

# Make sure we don't allow more than 300MB in case things go wrong
MAX_CHUNKS = 10000
CHUNK_SIZE = 30000


class Leaky(Process):
    def run(self):
        self._write('START')
        m = ' '
        chunks_count = 0
        while self.alive and chunks_count < MAX_CHUNKS:
            m += '*' * CHUNK_SIZE  # for memory
            chunks_count += 1

        self._write('STOP')


def run_leaky(test_file):
    process = Leaky(test_file)
    process.run()
    return 1


fqn = 'circus.tests.test_plugin_resource_watcher.run_leaky'


def get_statsd_increments(queue, plugin):
    queue.put(plugin.statsd.increments)


class TestResourceWatcher(TestCircus):

    def _check_statsd(self, increments, name):
        res = list(increments.items())
        self.assertTrue(len(res) > 0)
        for stat, items in res:
            if name == stat and items > 0:
                return
        raise AssertionError("%r stat not found" % name)

    def test_service_config_param_is_deprecated(self):
        with warnings.catch_warnings(record=True) as ws:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            self.make_plugin(ResourceWatcher, service='whatever')
            self.assertTrue(any('ResourceWatcher' in w.message.args[0]
                                for w in ws))

    def test_watcher_config_param_is_required(self):
        self.assertRaises(NotImplementedError, self.make_plugin,
                          ResourceWatcher)

    @gen_test
    def test_resource_watcher_max_mem(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'max_mem': 0.05, 'watcher': 'test'}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.over_memory')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_min_mem(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'min_mem': 100000.1, 'watcher': 'test'}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.under_memory')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_max_mem_abs(self):
        config = {'loop_rate': 0.1, 'max_mem_abs': '30M'}

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

    @gen_test
    def test_resource_watcher_min_mem_abs(self):
        config = {'loop_rate': 0.1, 'min_mem_abs': '100G'}

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
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'max_cpu': 0.1, 'watcher': 'test'}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.over_cpu')
        yield self.stop_arbiter()

    @gen_test
    def test_resource_watcher_min_cpu(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')
        config = {'loop_rate': 0.1, 'min_cpu': 99.0, 'watcher': 'test'}

        statsd_increments = yield async_run_plugin(ResourceWatcher,
                                                   config,
                                                   get_statsd_increments)

        self._check_statsd(statsd_increments,
                           '_resource_watcher.test.under_cpu')
        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)
