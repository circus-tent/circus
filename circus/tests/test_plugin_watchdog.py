import socket
import time
import os
from circus.tests.support import TestCircus, Process
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB)
from circus.plugins.watchdog import WatchDog


def run_plugin(klass, config, duration=300):
    endpoint = DEFAULT_ENDPOINT_DEALER
    pubsub_endpoint = DEFAULT_ENDPOINT_SUB
    check_delay = 1
    ssh_server = None

    plugin = klass(endpoint, pubsub_endpoint, check_delay, ssh_server,
                   **config)

    deadline = time.time() + (duration / 1000.)
    plugin.loop.add_timeout(deadline, plugin.stop)
    plugin.start()
    return plugin


class DummyWatchDogged(Process):
    def run(self):
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM)  # UDP
        my_pid = os.getpid()
        for _ in range(5):
            message = "{pid};{time}".format(pid=my_pid, time=time.time())
            print('sending:{0}'.format(message))
            sock.sendto(message, ('127.0.0.1', 1664))
            time.sleep(0.5)


def run_dummy_watchdogged(test_file):
    process = DummyWatchDogged()
    process.run()
    return 1


class TestPluginWatchDog(TestCircus):
    def setUp(self):
        super(TestPluginWatchDog, self).setUp()
        dummy_process = 'circus.tests.test_plugin_watchdog.run_dummy_watchdogged'
        self.test_file = self._run_circus(dummy_process)

    def test_watchdog_discovery_found(self):
        config = {'loop_rate': 0.3, 'watchers_regex': "^test.*$"}
        watchdog = run_plugin(WatchDog, config)
        time.sleep(.3)  # ensure at leat one loop in plugin
        self.assertEqual(len(watchdog.pid_status), 1)

    def test_watchdog_discovery_not_found(self):
        config = {'loop_rate': 0.3, 'watchers_regex': "^foo.*$"}
        watchdog = run_plugin(WatchDog, config)
        time.sleep(.3)  # ensure at leat one loop in plugin
        self.assertEqual(len(watchdog.pid_status), 0)

