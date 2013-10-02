import json
import os
import socket
import sys
import unittest

from mock import patch
import tornado
from tempfile import mkstemp
from time import time, sleep
from urlparse import urlparse

from circus.arbiter import Arbiter, ThreadedArbiter
from circus.client import CallError, CircusClient, make_message
from circus.plugins import CircusPlugin
from circus.tests.support import TestCircus, poll_for, truncate_file
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_MULTICAST,
                         DEFAULT_ENDPOINT_SUB)
from circus.watcher import Watcher
from circus.stream import QueueStream
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
        topic_parts = topic.split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        with open(self.config['file'], 'a+') as f:
            f.write('%s:%s' % (watcher, action))


class TestTrainer(TestCircus):

    @classmethod
    @tornado.gen.coroutine
    def setUpClass(cls):
        cmd = 'circus.tests.support.run_process'
        cls.stream = QueueStream()
        testfile, arbiter = cls._create_circus(
            cmd, stdout_stream={'stream': cls.stream},
            debug=True, async=True)
        cls.test_file = testfile
        cls.arbiter = arbiter
        yield cls.arbiter.start(start_ioloop=False)

    @classmethod
    @tornado.gen.coroutine
    def tearDownClass(cls):
        for watcher in cls.arbiter.iter_watchers():
            cls.arbiter.rm_watcher(watcher)
        yield cls.arbiter.stop(stop_ioloop=False)

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
        resp = yield self._call("numwatchers")
        self.assertTrue(resp.get("numwatchers") >= 1)

    @tornado.testing.gen_test
    def test_numprocesses(self):
        resp = yield self._call("numprocesses")
        self.assertTrue(resp.get("numprocesses") >= 1)

    @tornado.testing.gen_test
    def test_processes(self):
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

    @tornado.testing.gen_test
    def test_watchers(self):
        name = "test_watchers"
        resp = yield self._call("add", name=name,
                                cmd=self._get_cmd(),
                                start=True,
                                options=self._get_options())

        resp = yield self._call("list")
        self.assertTrue(name in resp.get('watchers'))

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
        resp = yield self._call("add", name="test_add_watcher",
                                cmd=self._get_cmd(),
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

    @tornado.testing.gen_test
    def test_add_watcher_arbiter_stopped(self):
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

    @tornado.testing.gen_test
    def test_add_watcher1(self):
        name = "test_add_watcher1"
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("list")
        self.assertTrue(name in resp.get('watchers'))

    @tornado.testing.gen_test
    def test_add_watcher2(self):
        resp = yield self._call("numwatchers")
        before = resp.get("numwatchers")

        name = "test_add_watcher2"
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         options=self._get_options())
        resp = yield self._call("numwatchers")
        self.assertEqual(resp.get("numwatchers"), before + 1)

    @tornado.testing.gen_test
    def test_add_watcher_already_exists(self):
        options = {'name': 'test_add_watcher3', 'cmd': self._get_cmd(),
                   'options': self._get_options()}

        yield self._call("add", **options)
        resp = yield self._call("add", **options)
        self.assertTrue(resp.get('status'), 'error')
        self.assertTrue(self.arbiter._exclusive_running_command is None)

    @tornado.testing.gen_test
    def test_add_watcher4(self):
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name="test_add_watcher4",
                                cmd=cmd, args=args,
                                options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

    @tornado.testing.gen_test
    def test_add_watcher5(self):
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

    @tornado.testing.gen_test
    def test_add_watcher6(self):
        name = 'test_add_watcher6'
        cmd, args = self._get_cmd_args()
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                start=True, options=self._get_options())
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")

    @tornado.testing.gen_test
    def test_add_watcher7(self):
        cmd, args = self._get_cmd_args()
        name = 'test_add_watcher7'
        resp = yield self._call("add", name=name, cmd=cmd, args=args,
                                start=True,
                                options=self._get_options(flapping_window=100))
        self.assertEqual(resp.get("status"), "ok")

        resp = yield self._call("status", name=name)
        self.assertEqual(resp.get("status"), "active")

        resp = yield self._call("options", name=name)
        options = resp.get('options', {})
        self.assertEqual(options.get("flapping_window"), 100)

    @tornado.testing.gen_test
    def test_rm_watcher(self):
        name = 'test_rm_watcher'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                          options=self._get_options())
        resp = yield self._call("numwatchers")
        before = resp.get("numwatchers")
        yield self._call("rm", name=name)
        resp = yield self._call("numwatchers")
        self.assertEqual(resp.get("numwatchers"), before - 1)

    @tornado.testing.gen_test
    def _test_stop(self):
        resp = yield self._call("quit")
        self.assertEqual(resp.get("status"), "ok")

    @tornado.testing.gen_test
    def test_reload(self):
        resp = yield self._call("reload")
        self.assertEqual(resp.get("status"), "ok")

    @tornado.testing.gen_test
    def test_reload1(self):
        name = 'test_reload1'
        yield self._call("add", name=name, cmd=self._get_cmd(),
                         start=True, options=self._get_options())

        resp = yield self._call("list", name=name)
        processes1 = resp.get('pids')

        truncate_file(self.test_file)  # clean slate

        yield self._call("reload")
        self.assertTrue(poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("list", name=name)
        processes2 = resp.get('pids')

        self.assertNotEqual(processes1, processes2)

    @tornado.testing.gen_test
    def test_reload2(self):
        resp = yield self._call("list", name="test")
        processes1 = resp.get('pids')
        self.assertEqual(len(processes1), 1)

        truncate_file(self.test_file)  # clean slate
        yield self._call("reload")
        self.assertTrue(poll_for(self.test_file, 'START'))  # restarted

        resp = yield self._call("list", name="test")
        processes2 = resp.get('pids')
        self.assertEqual(len(processes2), 1)
        self.assertNotEqual(processes1[0], processes2[0])

    @tornado.testing.gen_test
    def test_stop_watchers(self):
        yield self._call("stop")
        resp = yield self._call("status", name="test")
        self.assertEqual(resp.get("status"), "stopped")

        yield self._call("start")

        resp = yield self._call("status", name="test")
        self.assertEqual(resp.get("status"), 'active')

    @tornado.testing.gen_test
    def test_stop_watchers3(self):
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
        self.assertTrue(poll_for(datafile, 'PLUGIN STARTED'))

        cli = CircusClient()
        self.assertEqual(nb_processes(), 1)
        incr_processes()
        self.assertEqual(nb_processes(), 2)
        # wait for the plugin to receive the signal
        self.assertTrue(poll_for(datafile, 'test:spawn'))
        truncate_file(datafile)
        incr_processes()
        self.assertEqual(nb_processes(), 3)
        # wait for the plugin to receive the signal
        self.assertTrue(poll_for(datafile, 'test:spawn'))

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
            print endpoints

        self.assertTrue(resp)

    @tornado.testing.gen_test
    def test_start_watchers_warmup_delay(self):
        called = []

        @tornado.gen.coroutine
        def _sleep(duration):
            called.append(duration)
            loop = tornado.ioloop.IOLoop().instance()
            yield tornado.gen.Task(loop.add_timeout, time() + duration)

        watcher_mod.tornado_sleep = _sleep

        watcher = MockWatcher(name='foo', cmd='sleep 1', priority=1)
        resp = yield self.arbiter.start_watcher(watcher)

        self.assertTrue(called, [self.arbiter.warmup_delay])

        # now make sure we don't sleep when there is a autostart
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        yield self.arbiter.start_watcher(watcher)
        self.assertTrue(called, [self.arbiter.warmup_delay])



class MockWatcher(Watcher):

    def start(self):
        self.started = True


class TestArbiter(TestCircus):
    """
    Unit tests for the arbiter class to codify requirements within
    behavior.
    """
    @tornado.testing.gen_test
    def test_start_watcher(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1)
        arbiter = Arbiter([], None, None)
        yield arbiter.start_watcher(watcher)
        self.assertTrue(watcher.is_active())

    def test_start_watchers_with_autostart(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        arbiter = Arbiter([], None, None)
        arbiter.start_watcher(watcher)
        self.assertFalse(getattr(watcher, 'started', False))

    def test_add_watcher(self):
        arbiter = ThreadedArbiter([], DEFAULT_ENDPOINT_DEALER,
                                  DEFAULT_ENDPOINT_SUB)
        arbiter.add_watcher('foo', 'sleep 5')
        try:
            arbiter.start()
            sleep(.1)
            self.assertEqual(arbiter.watchers[0].status(), 'active')
        finally:
            arbiter.stop()
