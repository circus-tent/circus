import os
import signal
import socket
import tornado
from tempfile import mkstemp
from time import time
import zmq.utils.jsonapi as json
from unittest import mock
from urllib.parse import urlparse

from circus.arbiter import Arbiter
from circus.client import AsyncCircusClient
from circus.exc import AlreadyExist
from circus.plugins import CircusPlugin
from circus.tests.support import (TestCircus, async_poll_for, truncate_file,
                                  EasyTestSuite, skipIf, get_ioloop, SLEEP,
                                  PYTHON)
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_MULTICAST,
                         DEFAULT_ENDPOINT_SUB, to_str, IS_WINDOWS)
from circus.tests.support import (MockWatcher, has_circusweb,
                                  poll_for_callable, get_available_port)
from circus import watcher as watcher_mod


_GENERIC = os.path.join(os.path.dirname(__file__), 'generic.py')


class Plugin(CircusPlugin):
    name = 'dummy'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        with open(self.config['file'], 'a+') as f:
            f.write('PLUGIN STARTED')

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = to_str(topic).split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        with open(self.config['file'], 'a+') as f:
            f.write('%s:%s' % (watcher, action))


class TestTrainer(TestCircus):

    def setUp(self):
        super(TestTrainer, self).setUp()
        self.old = watcher_mod.tornado_sleep
        self.to_remove = []

    def tearDown(self):
        watcher_mod.tornado_sleep = self.old
        for path in self.to_remove:
            try:
                os.remove(path)
            except OSError:
                pass
        super(TestTrainer, self).tearDown()

    @tornado.gen.coroutine
    def _call(self, _cmd, **props):
        resp = yield self.call(_cmd, waiting=True, **props)
        raise tornado.gen.Return(resp)

    @tornado.testing.gen_test
    def test_numwatchers(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("numwatchers")
        self.assertTrue(resp.get("numwatchers") >= 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_numprocesses(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("numprocesses")
        self.assertTrue(resp.get("numprocesses") >= 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_processes(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_processes"
        resp = yield self._call("add", name=name,
                                cmd=self._get_cmd(),
                                start=True,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("list", name=name)
        self.assertEqual(len(resp.get('pids')), 1)

        resp = yield self._call("incr", name=name)
        self.assertEqual(resp.get('numprocesses'), 2)

        resp = yield self._call("incr", name=name, nb=2)
        self.assertEqual(resp.get('numprocesses'), 4)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_watchers(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_watchers"
        resp = yield self._call("add", name=name,
                                cmd=self._get_cmd(),
                                start=True,
                                options=self._get_options())

        resp = yield self._call("list")
        self.assertTrue(name in resp.get('watchers'))
        yield self.stop_arbiter()

    def _get_cmd(self):
        fd, testfile = mkstemp()
        os.close(fd)
        self.to_remove.append(testfile)
        cmd = '%s %s %s %s' % (
            PYTHON, _GENERIC,
            'circus.tests.support.run_process',
            testfile)

        return cmd

    def _get_cmd_args(self):
        cmd = PYTHON
        args = [_GENERIC, 'circus.tests.support.run_process']
        return cmd, args

    def _get_options(self, **kwargs):
        if 'graceful_timeout' not in kwargs:
            kwargs['graceful_timeout'] = 4
        return kwargs

    @tornado.testing.gen_test
    def test_add_watcher(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("add", name="test_add_watcher",
                                cmd=self._get_cmd(),
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher_arbiter_stopped(self):
        yield self.start_arbiter(graceful_timeout=0)
        # stop the arbiter
        resp = yield self._call("stop")
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("add",
                                name="test_add_watcher_arbiter_stopped",
                                cmd=self._get_cmd(),
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("start")
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher1(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_add_watcher1"
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("list")
        self.assertTrue(name in resp.get('watchers'))
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher2(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("numwatchers")
        before = resp.get("numwatchers")

        name = "test_add_watcher2"
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("numwatchers")
        self.assertEqual(resp.get("numwatchers"), before + 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher_already_exists(self):
        yield self.start_arbiter(graceful_timeout=0)
        options = {'name': 'test_add_watcher3', 'cmd': self._get_cmd(),
                   'options': self._get_options()}

        yield self._call("add", **options)
        resp = yield self._call("add", **options)
        self.assertTrue(resp.get('status'), 'error')
        self.assertTrue(self.arbiter._exclusive_running_command is None)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher4(self):
        yield self.start_arbiter(graceful_timeout=0)
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name="test_add_watcher4",
                                cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher5(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = "test_add_watcher5"
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name=name,
                                cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("start", name=name)
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher6(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_add_watcher6'
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                start=True, options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_add_watcher7(self):
        yield self.start_arbiter(graceful_timeout=0)
        cmd, args = self._get_cmd_args()
        name = 'test_add_watcher7'
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                start=True,
                                options=self._get_options(send_hup=True))
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")

        resp = yield self._call("options", name=name)
        options = resp.get('options', {})
        self.assertEqual(options.get("send_hup"), True)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_rm_watcher(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_rm_watcher'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("numwatchers")
        before = resp.get("numwatchers")
        yield self._call("rm", name=name)
        resp = yield self._call("numwatchers")
        self.assertEqual(resp.get("numwatchers"), before - 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_rm_watcher_nostop(self):
        # start watcher, save off the pids for the watcher processes we
        # started, stop the watcher without stopping processes, and validate
        # the processes are still running, then kill the processes
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_rm_watcher_nostop'
        yield self._call("add", name=name, cmd=self._get_cmd(), start=True,
                         options=self._get_options())
        resp = yield self._call("list", name=name)
        pids = resp.get('pids')
        self.assertEqual(len(pids), 1)
        yield self._call("rm", name=name, nostop=True)
        try:
            pid = pids[0]
            os.kill(pid, 0)
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
        except OSError:
            self.assertFalse(True, "process was incorrectly killed")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def _test_stop(self):
        resp = yield self._call("quit")
        self.assertEqual(resp.get("status"), "ok")

    @tornado.testing.gen_test
    def test_reload(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("reload")
        self.assertEqual(resp.get("status"), "ok")
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload1(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_reload1'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         start=True, options=self._get_options())

        resp = yield self._call("list", name=name)
        processes1 = resp.get('pids')

        truncate_file(self.test_file)  # clean slate

        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')
        self.assertTrue(res)  # restarted

        resp = yield self._call("list", name=name)
        processes2 = resp.get('pids')

        self.assertNotEqual(processes1, processes2)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_uppercase(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_RELOAD'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         start=True, options=self._get_options())

        resp = yield self._call("list", name=name)
        processes1 = resp.get('pids')

        truncate_file(self.test_file)  # clean slate

        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')
        self.assertTrue(res)  # restarted

        resp = yield self._call("list", name=name)
        processes2 = resp.get('pids')

        self.assertNotEqual(processes1, processes2)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_sequential(self):
        yield self.start_arbiter(graceful_timeout=0)
        name = 'test_reload_sequential'
        options = self._get_options(numprocesses=4)
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         start=True, options=options)
        resp = yield self._call("list", name=name)
        processes1 = resp.get('pids')
        truncate_file(self.test_file)  # clean slate
        yield self._call("reload", sequential=True)
        res = yield async_poll_for(self.test_file, 'START')  # restarted
        self.assertTrue(res)
        resp = yield self._call("list", name=name)
        processes2 = resp.get('pids')
        self.assertNotEqual(processes1, processes2)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload2(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("list", name="test")
        processes1 = resp.get('pids')
        self.assertEqual(len(processes1), 1)

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')  # restarted
        self.assertTrue(res)

        resp = yield self._call("list", name="test")
        processes2 = resp.get('pids')
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1[0], processes2[0])
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_wid_1_worker(self):
        yield self.start_arbiter(graceful_timeout=0)

        resp = yield self._call("stats", name="test")
        processes1 = list(resp['info'].keys())
        self.assertEqual(len(processes1), 1)
        wids1 = [resp['info'][process]['wid'] for process in processes1]
        self.assertEqual(wids1, [1])

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')  # restarted
        self.assertTrue(res)

        resp = yield self._call("stats", name="test")
        processes2 = list(resp['info'].keys())
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1, processes2)
        wids2 = [resp['info'][process]['wid'] for process in processes2]
        self.assertEqual(wids2, [2])

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')  # restarted
        self.assertTrue(res)

        resp = yield self._call("stats", name="test")
        processes3 = list(resp['info'].keys())
        self.assertEqual(len(processes3), 1)
        self.assertNotIn(processes3[0], (processes1[0], processes2[0]))
        wids3 = [resp['info'][process]['wid'] for process in processes3]
        self.assertEqual(wids3, [1])

        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_reload_wid_4_workers(self):
        yield self.start_arbiter(graceful_timeout=0)
        resp = yield self._call("incr", name="test", nb=3)
        self.assertEqual(resp.get('numprocesses'), 4)

        resp = yield self._call("stats", name="test")
        processes1 = list(resp['info'].keys())
        self.assertEqual(len(processes1), 4)
        wids1 = set(resp['info'][process]['wid'] for process in processes1)
        self.assertSetEqual(wids1, set([1, 2, 3, 4]))

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')  # restarted
        self.assertTrue(res)

        resp = yield self._call("stats", name="test")
        processes2 = list(resp['info'].keys())
        self.assertEqual(len(processes2), 4)
        self.assertEqual(len(set(processes1) & set(processes2)), 0)
        wids2 = set(resp['info'][process]['wid'] for process in processes2)
        self.assertSetEqual(wids2, set([5, 6, 7, 8]))

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        res = yield async_poll_for(self.test_file, 'START')  # restarted
        self.assertTrue(res)

        resp = yield self._call("stats", name="test")
        processes3 = list(resp['info'].keys())
        self.assertEqual(len(processes3), 4)
        self.assertEqual(len(set(processes1) & set(processes3)), 0)
        self.assertEqual(len(set(processes2) & set(processes3)), 0)
        wids3 = set([resp['info'][process]['wid'] for process in processes3])
        self.assertSetEqual(wids3, set([1, 2, 3, 4]))

        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_stop_watchers(self):
        yield self.start_arbiter(graceful_timeout=0)
        yield self._call("stop")
        resp = yield self._call("status", name="test")
        self.assertEqual(resp.get("status"), "stopped")

        yield self._call("start")

        resp = yield self._call("status", name="test")
        self.assertEqual(resp.get("status"), 'active')
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_stop_watchers3(self):
        yield self.start_arbiter(graceful_timeout=0)
        cmd, args = self._get_cmd_args()
        name = "test_stop_watchers3"
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("start", name=name)
        self.assertEqual(resp.get("status"), "ok")

        yield self._call("stop", name=name)
        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get('status'), "stopped")

        yield self._call("start", name=name)
        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get('status'), "active")
        yield self.stop_arbiter()

    @skipIf(IS_WINDOWS, "Streams not supported on Windows")
    @tornado.testing.gen_test
    def test_plugins(self):
        fd, datafile = mkstemp()
        os.close(fd)

        # setting up a circusd with a plugin
        plugin = 'circus.tests.test_arbiter.Plugin'
        plugins = [{'use': plugin, 'file': datafile}]

        yield self.start_arbiter(graceful_timeout=0, plugins=plugins,
                                 loop=get_ioloop())

        def incr_processes(cli):
            # return a coroutine if cli is Async
            return cli.send_message('incr', name='test')

        # wait for the plugin to be started
        res = yield async_poll_for(datafile, 'PLUGIN STARTED')
        self.assertTrue(res)

        cli = AsyncCircusClient(endpoint=self.arbiter.endpoint)

        res = yield cli.send_message('list', name='test')
        self.assertEqual(len(res.get('pids')), 1)

        yield incr_processes(cli)
        res = yield cli.send_message('list', name='test')
        self.assertEqual(len(res.get('pids')), 2)
        # wait for the plugin to receive the signal
        res = yield async_poll_for(datafile, 'test:spawn')
        self.assertTrue(res)
        truncate_file(datafile)

        yield incr_processes(cli)
        res = yield cli.send_message('list', name='test')
        self.assertEqual(len(res.get('pids')), 3)

        # wait for the plugin to receive the signal
        res = yield async_poll_for(datafile, 'test:spawn')
        self.assertTrue(res)
        os.remove(datafile)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_singleton(self):
        # yield self._stop_runners()
        yield self.start_arbiter(singleton=True, loop=get_ioloop())

        cli = AsyncCircusClient(endpoint=self.arbiter.endpoint)

        # adding more than one process should fail
        yield cli.send_message('incr', name='test')
        res = yield cli.send_message('list', name='test')
        self.assertEqual(len(res.get('pids')), 1)
        yield self.stop_arbiter()

    # TODO XXX
    @tornado.testing.gen_test
    def _test_udp_discovery(self):
        """test_udp_discovery: Test that when the circusd answer UDP call.

        """
        yield self._stop_runners()

        dummy_process = 'circus.tests.support.run_process'
        self._run_circus(dummy_process)

        ANY = '0.0.0.0'

        multicast_addr, multicast_port = urlparse(DEFAULT_ENDPOINT_MULTICAST)\
            .netloc.split(':')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        sock.bind((ANY, 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.sendto(json.dumps(''),
                    (multicast_addr, int(multicast_port)))

        timer = time()
        resp = False
        endpoints = []
        while time() - timer < 10:
            data, address = sock.recvfrom(1024)
            data = json.loads(data)
            endpoint = data.get('endpoint', "")

            if endpoint == DEFAULT_ENDPOINT_DEALER:
                resp = True
                break

            endpoints.append(endpoint)

        if not resp:
            print(endpoints)

        self.assertTrue(resp)

    # XXX TODO
    @tornado.testing.gen_test
    def _test_start_watchers_warmup_delay(self):
        yield self.start_arbiter()
        called = []

        @tornado.gen.coroutine
        def _sleep(duration):
            called.append(duration)
            yield tornado.gen.sleep(duration)

        watcher_mod.tornado_sleep = _sleep

        watcher = MockWatcher(name='foo', cmd=SLEEP % 1, priority=1)
        yield self.arbiter.start_watcher(watcher)

        self.assertTrue(called, [self.arbiter.warmup_delay])

        # now make sure we don't sleep when there is a autostart
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        yield self.arbiter.start_watcher(watcher)
        self.assertTrue(called, [self.arbiter.warmup_delay])
        yield self.stop_arbiter()


class TestArbiter(TestCircus):
    """
    Unit tests for the arbiter class to codify requirements within
    behavior.
    """
    def test_start_with_callback(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()
        arbiter = Arbiter([], controller, sub, check_delay=-1)

        callee = mock.MagicMock()

        def callback(*args):
            callee()
            arbiter.stop()

        arbiter.start(cb=callback)

        self.assertEqual(callee.call_count, 1)

    def test_start_with_callback_delay(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()
        arbiter = Arbiter([], controller, sub, check_delay=1)

        callee = mock.MagicMock()

        def callback(*args):
            callee()
            arbiter.stop()

        arbiter.start(cb=callback)

        self.assertEqual(callee.call_count, 1)

    @tornado.testing.gen_test
    def test_start_with_callback_and_given_loop(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()
        arbiter = Arbiter([], controller, sub, check_delay=-1,
                          loop=get_ioloop())

        callback = mock.MagicMock()

        try:
            yield arbiter.start(cb=callback)
        finally:
            yield arbiter.stop()

        self.assertEqual(callback.call_count, 0)

    @tornado.testing.gen_test
    def test_start_watcher(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1)
        arbiter = Arbiter([], None, None, check_delay=-1)
        yield arbiter.start_watcher(watcher)
        self.assertTrue(watcher.is_active())

    def test_start_watchers_with_autostart(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        arbiter = Arbiter([], None, None, check_delay=-1)
        arbiter.start_watcher(watcher)
        self.assertFalse(getattr(watcher, 'started', False))

    @tornado.testing.gen_test
    def test_add_watcher(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()
        arbiter = Arbiter([], controller, sub, loop=get_ioloop(),
                          check_delay=-1)
        arbiter.add_watcher('foo', SLEEP % 5)
        try:
            yield arbiter.start()
            self.assertEqual(arbiter.watchers[0].status(), 'active')
        finally:
            yield arbiter.stop()

    @tornado.testing.gen_test
    def test_start_arbiter_with_autostart(self):
        arbiter = Arbiter([], DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                          loop=get_ioloop(),
                          check_delay=-1)
        arbiter.add_watcher('foo', SLEEP % 5, autostart=False)
        try:
            yield arbiter.start()
            self.assertEqual(arbiter.watchers[0].status(), 'stopped')
        finally:
            yield arbiter.stop()

    @tornado.testing.gen_test
    def test_add_watcher_same_lowercase_names(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()
        arbiter = Arbiter([], controller, sub, loop=get_ioloop(),
                          check_delay=-1)
        arbiter.add_watcher('foo', SLEEP % 5)
        self.assertRaises(AlreadyExist, arbiter.add_watcher, 'Foo', SLEEP % 5)


@skipIf(not has_circusweb(), 'Tests for circus-web')
class TestCircusWeb(TestCircus):

    @tornado.testing.gen_test
    def test_circushttpd(self):
        controller = "tcp://127.0.0.1:%d" % get_available_port()
        sub = "tcp://127.0.0.1:%d" % get_available_port()

        arbiter = Arbiter([], controller, sub, loop=get_ioloop(),
                          check_delay=-1, httpd=True, debug=True)
        self.arbiters.append(arbiter)
        try:
            yield arbiter.start()
            poll_for_callable(self.assertDictEqual,
                              arbiter.statuses, {'circushttpd': 'active'})
        finally:
            yield arbiter.stop()


test_suite = EasyTestSuite(__name__)
