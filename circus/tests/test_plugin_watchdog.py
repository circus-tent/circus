import socket
import time
import os
import warnings
import multiprocessing

from tornado.gen import Return, coroutine
from tornado.testing import gen_test

from circus.tests.support import TestCircus, Process, poll_for
from circus.util import tornado_sleep
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB)
from circus.plugins.watchdog import WatchDog


def run_plugin(klass, config, queue, duration=300):
    endpoint = DEFAULT_ENDPOINT_DEALER
    pubsub_endpoint = DEFAULT_ENDPOINT_SUB
    check_delay = 1
    ssh_server = None

    plugin = klass(endpoint, pubsub_endpoint, check_delay, ssh_server,
                   **config)

    deadline = time.time() + (duration / 1000.)
    plugin.loop.add_timeout(deadline, plugin.stop)
    plugin.start()
    queue.put(plugin.pid_status)
    return plugin


@coroutine
def async_run_plugin(klass, config):
    queue = multiprocessing.Queue()
    circusctl_process = multiprocessing.Process(target=run_plugin,
                                                args=(klass, config, queue))
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
