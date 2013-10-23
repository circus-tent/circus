from mock import patch

from circus.tests.support import TestCircus, EasyTestSuite
from circus.plugins.flapping import Flapping
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB)


class TestFlapping(TestCircus):

    def setUp(self):
        super(TestFlapping, self).setUp()
        self.plugins = []

    def tearDown(self):
        for plugin in self.plugins:
            plugin.stop()
        super(TestFlapping, self).tearDown()

    def make_plugin(self, **config):
        config['active'] = True
        plugin = Flapping(DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                          1, None, **config)
        plugin.configs['test'] = {'active': True}
        plugin.timelines['test'] = [1, 2]
        self.plugins.append(plugin)
        return plugin

    def test_default_config(self):
        plugin = self.make_plugin()
        self.assertEqual(plugin.attempts, 2)
        self.assertEqual(plugin.window, 1)
        self.assertEqual(plugin.retry_in, 7)
        self.assertEqual(plugin.max_retry, 5)

    @patch.object(Flapping, 'check')
    def test_reap_message_calls_check(self, check_mock):
        plugin = self.make_plugin()
        topic = 'watcher.test.reap'

        plugin.handle_recv([topic, None])

        check_mock.assert_called_with('test')

    @patch.object(Flapping, 'cast')
    @patch('circus.plugins.flapping.Timer')
    def test_below_max_retry_triggers_restart(self, timer_mock, cast_mock):
        plugin = self.make_plugin(max_retry=5)
        plugin.tries['test'] = 4

        plugin.check('test')

        cast_mock.assert_called_with("stop", name="test")
        self.assertTrue(timer_mock.called)

    @patch.object(Flapping, 'cast')
    @patch('circus.plugins.flapping.Timer')
    def test_above_max_retry_triggers_final_stop(self, timer_mock, cast_mock):
        plugin = self.make_plugin(max_retry=5)
        plugin.tries['test'] = 5

        plugin.check('test')

        cast_mock.assert_called_with("stop", name="test")
        self.assertFalse(timer_mock.called)

    def test_beyond_window_resets_tries(self):
        plugin = self.make_plugin(max_retry=-1)
        plugin.tries['test'] = 1
        timestamp_beyond_window = plugin.window + plugin.check_delay + 1
        plugin.timelines['test'] = [0, timestamp_beyond_window]

        plugin.check('test')

        self.assertEqual(plugin.tries['test'], 0)

    @patch.object(Flapping, 'cast')
    @patch('circus.plugins.flapping.Timer')
    def test_minus_one_max_retry_triggers_restart(self, timer_mock, cast_mock):
        plugin = self.make_plugin(max_retry=-1)
        plugin.timelines['test'] = [1, 2]
        plugin.tries['test'] = 5

        plugin.check('test')

        cast_mock.assert_called_with("stop", name="test")
        self.assertTrue(timer_mock.called)

test_suite = EasyTestSuite(__name__)
