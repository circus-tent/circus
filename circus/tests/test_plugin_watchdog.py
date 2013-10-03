import socket
import time
import os
import warnings
from functools import partial
import multiprocessing

from tornado.gen import Return, coroutine
from tornado.testing import gen_test

from circus.tests.support import TestCircus, Process, poll_for, run_plugin
from circus.util import tornado_sleep
from circus.plugins.watchdog import WatchDog


def get_pid_status(queue, plugin):
    queue.put(plugin.pid_status)


@coroutine
def async_run_plugin(klass, config):
    queue = multiprocessing.Queue()
    circusctl_process = multiprocessing.Process(
        target=run_plugin,
        args=(klass, config, partial(get_pid_status, queue)))
    circusctl_process.start()
    while queue.empty():
        yield tornado_sleep(.1)
    pid_status = queue.get()
    raise Return(pid_status)


class DummyWatchDogged(Process):
    def run(self):
        self._write('START')
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM)  # UDP
        my_pid = os.getpid()
        for _ in range(5):
            message = "{pid};{time}".format(pid=my_pid, time=time.time())
            #print('sending:{0}'.format(message))
            sock.sendto(message, ('127.0.0.1', 1664))
            time.sleep(0.5)

        self._write('STOP')


def run_dummy_watchdogged(test_file):
    process = DummyWatchDogged(test_file)
    process.run()
    return 1


fqn = 'circus.tests.test_plugin_watchdog.run_dummy_watchdogged'


class TestPluginWatchDog(TestCircus):

    @gen_test
    def test_watchdog_discovery_found(self):
        yield self.start_arbiter(fqn)
        poll_for(self.test_file, 'START')

        config = {'loop_rate': 0.1, 'watchers_regex': "^test.*$"}
        with warnings.catch_warnings():
            pid_status = yield async_run_plugin(WatchDog, config)
        self.assertEqual(len(pid_status), 1, pid_status)
        yield self.stop_arbiter()

    @gen_test
    def test_watchdog_discovery_not_found(self):
        yield self.start_arbiter(fqn)
        poll_for(self.test_file, 'START')

        config = {'loop_rate': 0.1, 'watchers_regex': "^foo.*$"}
        with warnings.catch_warnings():
            pid_status = yield async_run_plugin(WatchDog, config)
        self.assertEqual(len(pid_status), 0, pid_status)
        yield self.stop_arbiter()
