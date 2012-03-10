import os
import sys
from tempfile import mkstemp
import time

from circus.client import CallError, CircusClient
from circus.tests.support import TestCircus

TEST_ENDPOINT="tcp://127.0.0.1:5555"

class DummyFly(object):

    def __init__(self):
        import signal
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def handle_quit(self, *args):
        self.alive = False

    def handle_chld(self, *args):
        pass

    def run(self):
        while self.alive:
            time.sleep(0.1)

def run_dummy(test_file):
    dummy = DummyFly()
    dummy.run()
    return 1

class TestTrainer(TestCircus):

    def setUp(self):
        super(TestTrainer, self).setUp()
        test_file = self._run_circus('circus.tests.test_trainer.run_dummy')
        time.sleep(0.5)
        self.cli = CircusClient(TEST_ENDPOINT)

    def tearDown(self):
        super(TestTrainer, self).tearDown()
        self.cli.stop()

    def test_numshows(self):
        resp = self.cli.call("numshows")
        self.assertEqual(resp, "1")

    def test_numflies(self):
        resp = self.cli.call("numflies")
        self.assertEqual(resp, "1")

    def test_flies(self):
        resp = self.cli.call("flies")
        self.assertEqual(resp, "test: 1")

    def test_shows(self):
        resp = self.cli.call("shows")
        self.assertEqual(resp, "test")

    def _get_cmd(self):
        fd, testfile = mkstemp()
        os.close(fd)
        cmd = '%s generic.py %s %s' % (sys.executable,
                        'circus.tests.test_trainer.run_dummy', testfile)

        return cmd

    def test_add_show(self):
        cmd = self._get_cmd()
        resp = self.cli.call("add_show test1 %s" % cmd)
        self.assertEqual(resp, "ok")

    def test_add_show1(self):
        cmd = self._get_cmd()
        self.cli.call("add_show test1 %s" % cmd)
        resp = self.cli.call("shows")
        self.assertTrue(resp.endswith("test1"))

    def test_add_show2(self):
        cmd = self._get_cmd()
        self.cli.call("add_show test1 %s" % cmd)
        self.cli.call("shows")
        resp = self.cli.call("numshows")
        self.assertEqual(resp, "2")

    def test_del_show(self):
        cmd = self._get_cmd()
        self.cli.call("add_show test1 %s" % cmd)
        self.cli.call("del_show test1")
        resp = self.cli.call("numshows")
        self.assertEqual(resp, "1")

    def test_stop(self):
        self.cli.call("stop")
        self.assertRaises(CallError, self.cli.call, "shows")
