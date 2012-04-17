import time
import signal
import sys
import os

from circus.client import CircusClient, make_message
from circus.tests.support import TestCircus
from circus.stream import QueueStream


def run_process(test_file):
    try:
        i = 0
        while True:
            sys.stdout.write('%d-%s\\n' % (os.getpid(), i))
            sys.stdout.flush()
            time.sleep(1)
    except:
        return 1


class TestWatcher(TestCircus):

    def setUp(self):
        super(TestWatcher, self).setUp()
        self.stream = QueueStream()
        dummy_process = 'circus.tests.test_watcher.run_process'
        self.test_file = self._run_circus(dummy_process,
                stdout_stream={'stream': self.stream})
        self.cli = CircusClient()

    def call(self, cmd, **props):
        msg = make_message(cmd, **props)
        return self.cli.call(msg)

    def tearDown(self):
        super(TestWatcher, self).tearDown()
        self.cli.stop()

    def status(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('status')

    def numprocesses(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numprocesses')

    def testSignal(self):
        self.assertEquals(self.numprocesses("incr", name="test"), 2)
        self.assertEquals(self.call("list", name="test").get('processes'),
                          [1, 2])
        self.assertEquals(self.status("signal", name="test", process=2,
            signum=signal.SIGKILL), "ok")

        time.sleep(1.0)
        self.assertEquals(self.call("list", name="test").get('processes'),
                          [1, 3])

        processes = self.call("list", name="test").get('processes')
        self.assertEquals(self.status("signal", name="test",
            signum=signal.SIGKILL), "ok")

        time.sleep(1.0)
        self.assertNotEqual(self.call("list", name="test").get('processes'),
                processes)

    def testStats(self):
        resp = self.call("stats").get('infos')
        self.assertTrue("test" in resp)

        self.assertEqual(resp['test']['1']['cmdline'],
                         sys.executable.split(os.sep)[-1])

    def test_streams(self):
        time.sleep(2.)
        # let's see what we got
        self.assertTrue(self.stream.qsize() > 1)
