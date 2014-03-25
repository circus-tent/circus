import os
import socket
import sys
import tornado
from tempfile import mkstemp
from time import time
import zmq.utils.jsonapi as json
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse  # NOQA

from circus.arbiter import Arbiter
from circus.client import CircusClient
from circus.plugins import CircusPlugin
from circus.tests.support import TestCircus, async_poll_for, truncate_file
from circus.tests.support import EasyTestSuite, skipIf, get_ioloop
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_MULTICAST,
                         DEFAULT_ENDPOINT_SUB)
from circus.watcher import Watcher
from circus.tests.support import (has_circusweb, poll_for_callable,
                                  get_available_port)
from circus import watcher as watcher_mod
from circus.py3compat import s


_GENERIC = os.path.join(os.path.dirname(__file__), 'generic.py')


class Plugin(CircusPlugin):
    name = 'dummy'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        with open(self.config['file'], 'a+') as f:
            f.write('PLUGIN STARTED')

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = s(topic).split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        with open(self.config['file'], 'a+') as f:
            f.write('%s:%s' % (watcher, action))


class TestTrainer(TestCircus):

    def setUp(self):
        super(TestTrainer, self).setUp()
        self.old = watcher_mod.tornado_sleep

    def tearDown(self):
        watcher_mod.tornado_sleep = self.old
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
        cmd = '%s %s %s %s' % (
            sys.executable, _GENERIC,
            'circus.tests.support.run_process',
            testfile)

        return cmd

    def _get_cmd_args(self):
        cmd = sys.executable
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
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

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
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted
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
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

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
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("stats", name="test")
        processes2 = list(resp['info'].keys())
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1, processes2)
        wids2 = [resp['info'][process]['wid'] for process in processes2]
        self.assertEqual(wids2, [2])

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

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
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("stats", name="test")
        processes2 = list(resp['info'].keys())
        self.assertEqual(len(processes2), 4)
        self.assertEqual(len(set(processes1) & set(processes2)), 0)
        wids2 = set(resp['info'][process]['wid'] for process in processes2)
        self.assertSetEqual(wids2, set([5, 6, 7, 8]))

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(async_poll_for(self.test_file, 'START'))  # restarted

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

    # XXX TODO
    @tornado.testing.gen_test
    def _test_plugins(self):

        fd, datafile = mkstemp()
        os.close(fd)

        # setting up a circusd with a plugin
        dummy_process = 'circus.tests.support.run_process'
        plugin = 'circus.tests.test_arbiter.Plugin'
        plugins = [{'use': plugin, 'file': datafile}]
        self._run_circus(dummy_process, plugins=plugins)

        # doing a few operations
        def nb_processes():
            return len(cli.send_message('list', name='test').get('pids'))

        def incr_processes():
            return cli.send_message('incr', name='test')

        # wait for the plugin to be started
        self.assertTrue(async_poll_for(datafile, 'PLUGIN STARTED'))

        cli = CircusClient()
        self.assertEqual(nb_processes(), 1)
        incr_processes()
        self.assertEqual(nb_processes(), 2)
        # wait for the plugin to receive the signal
        self.assertTrue(async_poll_for(datafile, 'test:spawn'))
        truncate_file(datafile)
        incr_processes()
        self.assertEqual(nb_processes(), 3)
        # wait for the plugin to receive the signal
        self.assertTrue(async_poll_for(datafile, 'test:spawn'))

    # XXX TODO
    @tornado.testing.gen_test
    def _test_singleton(self):
        self._stop_runners()

        dummy_process = 'circus.tests.support.run_process'
        self._run_circus(dummy_process, singleton=True)
        cli = CircusClient()

        # adding more than one process should fail
        res = cli.send_message('incr', name='test')
        self.assertEqual(res['numprocesses'], 1)

    # TODO XXX
    @tornado.testing.gen_test
    def _test_udp_discovery(self):
        """test_udp_discovery: Test that when the circusd answer UDP call.

        """
        self._stop_runners()

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
            loop = get_ioloop()
            yield tornado.gen.Task(loop.add_timeout, time() + duration)

        watcher_mod.tornado_sleep = _sleep

        watcher = MockWatcher(name='foo', cmd='sleep 1', priority=1)
        yield self.arbiter.start_watcher(watcher)

        self.assertTrue(called, [self.arbiter.warmup_delay])

        # now make sure we don't sleep when there is a autostart
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        yield self.arbiter.start_watcher(watcher)
        self.assertTrue(called, [self.arbiter.warmup_delay])
        yield self.stop_arbiter()


class MockWatcher(Watcher):

    def start(self):
        self.started = True

    def spawn_process(self):
        self.processes[1] = 'dummy'


class TestArbiter(TestCircus):
    """
    Unit tests for the arbiter class to codify requirements within
    behavior.
    """
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
        arbiter.add_watcher('foo', 'sleep 5')
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
        arbiter.add_watcher('foo', 'sleep 5', autostart=False)
        try:
            yield arbiter.start()
            self.assertEqual(arbiter.watchers[0].status(), 'stopped')
        finally:
            yield arbiter.stop()


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
