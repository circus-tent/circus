import time
import signal

from circus.client import CircusClient, make_message
from circus.tests.support import TestCircus


def run_process(test_file):
    try:
        while True:
            time.sleep(1)
    except:
        return 1


class TestWatcher(TestCircus):

    def setUp(self):
        super(TestWatcher, self).setUp()
        dummy_process = 'circus.tests.test_watcher.run_process'
        self.test_file = self._run_circus(dummy_process)
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

        self.assertEqual(resp['test']['1']['cmdline'], 'python')
