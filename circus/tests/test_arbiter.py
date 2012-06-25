import os
import sys
from tempfile import mkstemp
import time

from circus.client import CallError, CircusClient, make_message
from circus.tests.support import TestCircus
from circus.plugins import CircusPlugin


class DummyProcess(object):

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
    dummy = DummyProcess(test_file)
    dummy.run()
    return 1


class Plugin(CircusPlugin):
    name = 'dummy'

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = topic.split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        with open(self.config['file'], 'a+') as f:
            f.write('%s:%s\n' % (watcher, action))


class DummyProcess1(object):

    def __init__(self):
        import signal
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)

    def handle_quit(self, *args):
        self.alive = False

    def handle_chld(self, *args):
        pass

    def run(self):
        self.alive = True
        while self.alive:
            time.sleep(0.1)


def run_dummy1():
    dummy1 = DummyProcess1()
    dummy1.run()


class TestTrainer(TestCircus):

    def setUp(self):
        super(TestTrainer, self).setUp()
        dummy_process = 'circus.tests.test_arbiter.run_dummy'
        self.test_file = self._run_circus(dummy_process)
        self.cli = CircusClient()

    def tearDown(self):
        super(TestTrainer, self).tearDown()
        self.cli.stop()

    def test_numwatchers(self):
        msg = make_message("numwatchers")
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("numwatchers"), 1)

    def test_numprocesses(self):
        msg = make_message("numprocesses")
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("numprocesses"), 1)

    def test_processes(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        self.assertEqual(len(resp.get('pids')), 1)

        msg2 = make_message("incr", name="test")
        self.cli.call(msg2)

        resp = self.cli.call(msg1)
        self.assertEqual(len(resp.get('pids')), 2)

        self.cli.send_message("incr", name="test", nb=2)
        resp = self.cli.call(msg1)
        self.assertEqual(len(resp.get('pids')), 4)

    def test_watchers(self):
        resp = self.cli.call(make_message("list"))
        self.assertEqual(resp.get('watchers'), ["test"])

    def _get_cmd(self):
        fd, testfile = mkstemp()
        os.close(fd)
        cmd = '%s generic.py %s %s' % (sys.executable,
                        'circus.tests.test_arbiter.run_dummy', testfile)

        return cmd

    def _get_cmd_args(self):
        cmd = sys.executable
        args = ['generic.py', 'circus.tests.test_arbiter.run_dummy1']
        return cmd, args

    def _get_options(self, **kwargs):
        if 'graceful_timeout' not in kwargs:
            kwargs['graceful_timeout'] = 4
        return kwargs

    def test_add_watcher(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd(),
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

    def test_add_watcher1(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(make_message("list"))
        self.assertEqual(resp.get('watchers'), ["test", "test1"])

    def test_add_watcher2(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(make_message("numwatchers"))
        self.assertEqual(resp.get("numwatchers"), 2)

    def test_add_watcher3(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(msg)
        self.assertTrue(resp.get('status'), 'error')

    def test_add_watcher4(self):
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name="test1", cmd=cmd, args=args,
                options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

    def test_add_watcher5(self):
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name="test1", cmd=cmd, args=args,
                options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")
        resp = self.cli.call(make_message("start", name="test1"))
        self.assertEqual(resp.get("status"), "ok")
        resp = self.cli.call(make_message("status", name="test1"))
        self.assertEqual(resp.get("status"), "active")

    def test_add_watcher6(self):
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name="test1", cmd=cmd, args=args,
                           start=True, options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

        resp = self.cli.call(make_message("status", name="test1"))
        self.assertEqual(resp.get("status"), "active")

    def test_add_watcher7(self):
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name="test1", cmd=cmd, args=args, start=True,
                           options=self._get_options(flapping_window=100))
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

        resp = self.cli.call(make_message("status", name="test1"))
        self.assertEqual(resp.get("status"), "active")

        resp = self.cli.call(make_message("options", name="test1"))
        options = resp.get('options', {})
        self.assertEqual(options.get("flapping_window"), 100)

    def test_rm_watcher(self):
        msg = make_message("add", name="test1", cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        msg = make_message("rm", name="test1")
        self.cli.call(msg)
        resp = self.cli.call(make_message("numwatchers"))
        self.assertEqual(resp.get("numwatchers"), 1)

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
        processes1 = resp.get('pids')

        self.cli.call(make_message("reload"))
        time.sleep(0.5)

        msg2 = make_message("list", name="test")
        resp = self.cli.call(msg2)
        processes2 = resp.get('pids')

        self.assertNotEqual(processes1, processes2)

    def test_reload2(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        processes1 = resp.get('pids')
        self.assertEqual(len(processes1), 1)

        self.cli.call(make_message("reload"))
        time.sleep(0.5)

        make_message("list", name="test")
        resp = self.cli.call(msg1)

        processes2 = resp.get('pids')
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1[0], processes2[0])

    def test_stop_watchers(self):
        resp = self.cli.call(make_message("stop"))
        self.assertEqual(resp.get("status"), "ok")

    def test_stop_watchers1(self):
        self.cli.call(make_message("stop"))
        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get("status"), "stopped")

    def test_stop_watchers2(self):
        self.cli.call(make_message("stop", name="test"))
        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get('status'), "stopped")

    def test_stop_watchers3(self):
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name="test1", cmd=cmd, args=args,
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")
        resp = self.cli.call(make_message("start", name="test1"))
        self.assertEqual(resp.get("status"), "ok")

        self.cli.call(make_message("stop", name="test1"))
        resp = self.cli.call(make_message("status", name="test1"))
        self.assertEqual(resp.get('status'), "stopped")

        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get('status'), "active")

    def test_plugins(self):
        # killing the setUp runner
        self._stop_runners()
        self.cli.stop()

        fd, datafile = mkstemp()
        os.close(fd)

        # setting up a circusd with a plugin
        dummy_process = 'circus.tests.test_arbiter.run_dummy'
        plugin = 'circus.tests.test_arbiter.Plugin'
        plugins = [{'use': plugin, 'file': datafile}]
        self._run_circus(dummy_process, plugins=plugins)

        # doing a few operations
        def nb_processes():
            return len(cli.send_message('list', name='test').get('pids'))

        def incr_processes():
            return cli.send_message('incr', name='test')

        cli = CircusClient()
        self.assertEqual(nb_processes(), 1)
        incr_processes()
        self.assertEqual(nb_processes(), 2)
        incr_processes()
        self.assertEqual(nb_processes(), 3)

        # wait a bit
        time.sleep(.2)

        # checking what the plugin did
        with open(datafile) as f:
            data = [line for line in f.read().split('\n')
                    if line != '']

        wanted = ['test:spawn', 'test:spawn']
        self.assertEqual(data, wanted)

    def test_singleton(self):
        self._stop_runners()

        dummy_process = 'circus.tests.test_arbiter.run_dummy'
        self._run_circus(dummy_process, singleton=True)
        cli = CircusClient()

        # adding more than one process should fail
        res = cli.send_message('incr', name='test')
        self.assertEqual(res['numprocesses'], 1)
