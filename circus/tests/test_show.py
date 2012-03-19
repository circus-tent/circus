import time
import signal

from circus.client import CircusClient, make_message
from circus.tests.support import TestCircus

def run_fly(test_file):
    try:
        while True:
            time.sleep(1)
    except:
        return 1

class TestShow(TestCircus):

    def setUp(self):
        super(TestShow, self).setUp()
        dummy_fly = 'circus.tests.test_show.run_fly'
        self.test_file = self._run_circus(dummy_fly)
        self.cli = CircusClient()

    def call(self, cmd, **props):
        msg = make_message(cmd, **props)
        return self.cli.call(msg)

    def tearDown(self):
        super(TestShow, self).tearDown()
        self.cli.stop()

    def status(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('status')

    def numflies(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numflies')

    def testSignal(self):
        self.assertEquals(self.numflies("incr", name="test"), 2)
        self.assertEquals(self.call("list", name="test").get('flies'), [1, 2])
        self.assertEquals(self.status("signal", name="test", fly=2,
            signum=signal.SIGKILL), "ok")

        time.sleep(1.0)
        self.assertEquals(self.call("list", name="test").get('flies'), [1, 3])

        flies = self.call("list", name="test").get('flies')
        self.assertEquals(self.status("signal", name="test",
            signum=signal.SIGKILL), "ok")

        time.sleep(1.0)
        self.assertNotEqual(self.call("list", name="test").get('flies'),
                flies)

    def testStats(self):
        resp = self.call("stats").get('infos')
        self.assertTrue("test" in resp)

        self.assertEqual(resp['test']['1']['cmdline'], 'python')
