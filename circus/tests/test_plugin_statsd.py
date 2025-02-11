from tornado.testing import gen_test

from circus.tests.support import TestCircus, async_poll_for
from circus.tests.support import async_run_plugin, EasyTestSuite
from circus.plugins.statsd import FullStats


def get_gauges(queue, plugin):
    queue.put(plugin.statsd.gauges)


class TestFullStats(TestCircus):

    @gen_test
    def test_full_stats(self):
        dummy_process = 'circus.tests.support.run_process'
        yield self.start_arbiter(dummy_process)
        yield async_poll_for(self.test_file, 'START')

        config = {'loop_rate': 0.2}
        gauges = yield async_run_plugin(
            FullStats, config,
            plugin_info_callback=get_gauges,
            duration=1000,
            endpoint=self.arbiter.endpoint,
            pubsub_endpoint=self.arbiter.pubsub_endpoint)

        # we should have a bunch of stats events here
        self.assertTrue(len(gauges) >= 5)
        last_batch = sorted(name for name, value in gauges[-5:])
        wanted = ['_stats.test.cpu_sum', '_stats.test.mem_max',
                  '_stats.test.mem_pct_max', '_stats.test.mem_pct_sum',
                  '_stats.test.mem_sum']
        self.assertEqual(last_batch, wanted)

        yield self.stop_arbiter()


test_suite = EasyTestSuite(__name__)
