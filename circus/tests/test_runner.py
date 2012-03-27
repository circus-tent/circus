import os
import time
import sys
import threading
import signal

from circus.tests.support import TestCircus
from circus.watcher import Watcher
from circus.arbiter import Arbiter
from circus.circusd import main


def Dummy(test_file):
    with open(test_file, 'w') as f:
        f.write('..........')
    return 1


class TestRunner(TestCircus):

    def test_dummy(self):
        test_file = self._run_circus('circus.tests.test_runner.Dummy')
        time.sleep(1.)

        # check that the file has been filled
        with open(test_file) as f:
            content = f.read()

        self.assertTrue('.' in content)

    def test_issue53(self):
        watcher = Watcher('test', 'bash -q', numprocesses=10,
                          warmup_delay=0)
        endpoint = 'tcp://127.0.0.1:5555'
        pubsub_endpoint = 'tcp://127.0.0.1:5556'
        arbiter = Arbiter([watcher], endpoint, pubsub_endpoint, check_delay=0.1)

        def handler(signum, frame):
            arbiter.stop()

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(10)

        arbiter.start()
