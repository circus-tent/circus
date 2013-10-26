import socket
import time
import os
import warnings

from tornado.testing import gen_test

from circus.tests.support import TestCircus, Process, async_poll_for
from circus.tests.support import async_run_plugin, EasyTestSuite
from circus.plugins.watchdog import WatchDog


class DummyWatchDogged(Process):
    def run(self):
        self._write('START')
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM)  # UDP
        try:
            my_pid = os.getpid()
            for _ in range(5):
                message = "{pid};{time}".format(pid=my_pid, time=time.time())
                sock.sendto(message, ('127.0.0.1', 1664))
                time.sleep(0.5)
            self._write('STOP')
        finally:
            sock.close()


def run_dummy_watchdogged(test_file):
    process = DummyWatchDogged(test_file)
    process.run()
    return 1


def get_pid_status(queue, plugin):
    queue.put(plugin.pid_status)


fqn = 'circus.tests.test_plugin_watchdog.run_dummy_watchdogged'


class TestPluginWatchDog(TestCircus):

    @gen_test
    def test_watchdog_discovery_found(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')

        config = {'loop_rate': 0.1, 'watchers_regex': "^test.*$"}
        with warnings.catch_warnings():
            pid_status = yield async_run_plugin(WatchDog, config,
                                                get_pid_status)
        self.assertEqual(len(pid_status), 1, pid_status)
        yield self.stop_arbiter()

    @gen_test
    def test_watchdog_discovery_not_found(self):
        yield self.start_arbiter(fqn)
        async_poll_for(self.test_file, 'START')

        config = {'loop_rate': 0.1, 'watchers_regex': "^foo.*$"}
        with warnings.catch_warnings():
            pid_status = yield async_run_plugin(WatchDog, config,
                                                get_pid_status)
        self.assertEqual(len(pid_status), 0, pid_status)
        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)
