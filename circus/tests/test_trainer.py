import os
import sys
from tempfile import mkstemp
import time

from circus.client import CallError, CircusClient
from circus.tests.support import TestCircus

class DummyFly(object):

    def __init__(self, testfile):
        self.alive = True
        self.testfile = testfile

        import signal
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)

    def _write(self, msg):
        with open(self.testfile, 'a+') as f:
            f.write(msg)

    def handle_quit(self, *args):
        self._write('QUIT')
        self.alive = False

    def handle_chld(self, *args):
        self._write('CHLD')

    def run(self):
        self._write('START')
        while self.alive:
            time.sleep(0.1)
        self._write('STOP')

def run_dummy(test_file):
    dummy = DummyFly(test_file)
    dummy.run()
    return 1

class TestTrainer(TestCircus):

    def setUp(self):
        super(TestTrainer, self).setUp()
        dummy_fly = 'circus.tests.test_trainer.run_dummy'
        self.test_file = self._run_circus(dummy_fly)
        self.cli = CircusClient()

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
        resp = self.cli.call("list test")
        self.assertEqual(resp, "1")
        self.cli.call("incr test")
        resp = self.cli.call("list test")
        self.assertEqual(resp, "1,2")

    def test_shows(self):
        resp = self.cli.call("list")
        self.assertEqual(resp, "test")

    def _get_cmd(self):
        fd, testfile = mkstemp()
        os.close(fd)
        cmd = '%s generic.py %s %s' % (sys.executable,
                        'circus.tests.test_trainer.run_dummy', testfile)

        return cmd

    def test_add_show(self):
        cmd = self._get_cmd()
        resp = self.cli.call("add test1 %s" % cmd)
        self.assertEqual(resp, "ok")

    def test_add_show1(self):
        cmd = self._get_cmd()
        self.cli.call("add test1 %s" % cmd)
        resp = self.cli.call("list")
        self.assertTrue(resp.endswith("test1"))

    def test_add_show2(self):
        cmd = self._get_cmd()
        self.cli.call("add test1 %s" % cmd)
        resp = self.cli.call("numshows")
        self.assertEqual(resp, "2")

    def test_add_show3(self):
        cmd = self._get_cmd()
        self.cli.call("add test1 %s" % cmd)
        resp = self.cli.call("add test1 %s" % cmd)
        self.assertTrue(resp.startswith("error:"))

    def test_rm_show(self):
        cmd = self._get_cmd()
        self.cli.call("add test1 %s" % cmd)
        self.cli.call("rm test1")
        resp = self.cli.call("numshows")
        self.assertEqual(resp, "1")

    def test_stop(self):
        resp = self.cli.call("quit")
        self.assertEqual(resp, "ok")
        self.assertRaises(CallError, self.cli.call, "list")

    def test_reload(self):
        resp = self.cli.call("reload")
        self.assertEqual(resp, "ok")


    def test_reload1(self):
        flies0 = self.cli.call("list test")
        resp = self.cli.call("reload")
        time.sleep(0.5)
        flies1 = self.cli.call("list test")
        self.assertNotEqual(flies0, flies1)

    def test_reload(self):
        flies1 = self.cli.call("list test")
        self.assertEqual(flies1, "1")
        self.cli.call("reload")
        time.sleep(0.5)
        flies = self.cli.call("list test")
        self.assertEqual(flies, "2")

    def test_stop_shows(self):
        resp = self.cli.call("stop")
        self.assertEqual(resp, "ok")

    def test_stop_shows1(self):
        self.cli.call("stop")
        resp = self.cli.call("status test")
        self.assertEqual(resp, "stopped")

    def test_stop_shows(self):
        self.cli.call("stop test")
        resp = self.cli.call("status test")
        self.assertEqual(resp, "stopped")
