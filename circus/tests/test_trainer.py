import os
import sys
from tempfile import mkstemp
import time

from zmq.utils.jsonapi import jsonmod as json

from circus.client import CallError, CircusClient, make_message
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
        msg = make_message("numshows")
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("numshows"), 1)

    def test_numflies(self):
        msg = make_message("numflies")
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("numflies"), 1)

    def test_flies(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        self.assertEqual(resp.get('flies'), [1])

        msg2 = make_message("incr", name="test")
        self.cli.call(msg2)

        resp = self.cli.call(msg1)
        self.assertEqual(resp.get('flies'), [1, 2])

    def test_shows(self):
        resp = self.cli.call(make_message("list"))
        self.assertEqual(resp.get('shows'), ["test"])

    def _get_cmd(self):
        fd, testfile = mkstemp()
        os.close(fd)
        cmd = '%s generic.py %s %s' % (sys.executable,
                        'circus.tests.test_trainer.run_dummy', testfile)

        return cmd

    def test_add_show(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

    def test_add_show1(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd())
        self.cli.call(msg)
        resp = self.cli.call(make_message("list"))
        self.assertEqual(resp.get('shows'), ["test", "test1"])

    def test_add_show2(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd())
        self.cli.call(msg)
        resp = self.cli.call(make_message("numshows"))
        self.assertEqual(resp.get("numshows"), 2)

    def test_add_show3(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd())
        self.cli.call(msg)
        resp = self.cli.call(msg)
        self.assertTrue(resp.get('status'), 'error')

    def test_rm_show(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd())
        self.cli.call(msg)
        msg = make_message("rm", name="test1")
        self.cli.call(msg)
        resp = self.cli.call(make_message("numshows"))
        self.assertEqual(resp.get("numshows"), 1)

    def test_stop(self):
        resp = self.cli.call(make_message("quit"))
        self.assertEqual(resp.get("status"), "ok")
        self.assertRaises(CallError, self.cli.call, make_message("list"))

    def test_reload(self):
        resp = self.cli.call(make_message("reload"))
        self.assertEqual(resp.get("status"), "ok")

    def test_reload1(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        flies1 = resp.get('flies')

        self.cli.call(make_message("reload"))
        time.sleep(0.5)

        msg2 = make_message("list", name="test")
        resp = self.cli.call(msg2)
        flies2 = resp.get('flies')

        self.assertNotEqual(flies1, flies2)

    def test_reload2(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        flies1 = resp.get('flies')
        self.assertEqual(flies1, [1])

        self.cli.call(make_message("reload"))
        time.sleep(0.5)

        msg2 = make_message("list", name="test")
        resp = self.cli.call(msg1)

        flies2 = resp.get('flies')
        self.assertEqual(flies2, [2])

    def test_stop_shows(self):
        resp = self.cli.call(make_message("stop"))
        self.assertEqual(resp.get("status"), "ok")

    def test_stop_shows1(self):
        self.cli.call(make_message("stop"))
        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get("status"), "stopped")

    def test_stop_shows2(self):
        self.cli.call(make_message("stop", name="test"))
        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get('status'), "stopped")

