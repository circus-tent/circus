from circus.tests.support import TestCircus, poll_for, run_plugin
from circus.plugins.statsd import FullStats


class TestFullStats(TestCircus):
    def setUp(self):
        super(TestFullStats, self).setUp()
        dummy_process = 'circus.tests.support.run_process'
        self.test_file = self._run_circus(dummy_process)
        poll_for(self.test_file, 'START')

    def test_full_stats(self):
        config = {'loop_rate': 0.2}
        _statsd = run_plugin(FullStats, config, 1000)

        # we should have a bunch of stats events here
        self.assertTrue(len(_statsd.gauges) >= 5)
        last_batch = [name for name, value in _statsd.gauges[-5:]]
        last_batch.sort()
        wanted = ['_stats.test.cpu_max', '_stats.test.cpu_sum',
                  '_stats.test.mem_max', '_stats.test.mem_sum',
                  '_stats.test.watchers_num']
        self.assertEqual(last_batch, wanted)
