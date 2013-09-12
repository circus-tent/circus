import json
import os
import socket
import sys
import unittest2 as unittest

from mock import patch
from tempfile import mkstemp
from time import time
from urlparse import urlparse

from circus.client import CallError, CircusClient, make_message
from circus.plugins import CircusPlugin
from circus.tests.support import (poll_for, truncate_file,
                                  create_circus)
from circus.util import DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_MULTICAST
from circus.watcher import Watcher
from circus import get_arbiter


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


def _setUpClass(cls, fqn='circus.tests.support.run_process',
                client_factory=CircusClient, **kw):
    cls.test_file, cls.arb = create_circus(fqn, **kw)
    cls.cli = client_factory()
    poll_for(cls.test_file, 'START')


def _tearDownClass(cls):
    cls.cli.stop()
    cls.arb.stop()


class _TestTrainer(object):

    @classmethod
    def setUpClass(cls):
        _setUpClass(cls, factory=cls._get_arbiter_factory(),
                    client_factory=cls._get_client_factory())

    @classmethod
    def tearDownClass(cls):
        _tearDownClass(cls)

    @classmethod
    def _get_arbiter_factory(cls):
        return get_arbiter

    @classmethod
    def _get_client_factory(cls):
        return CircusClient

    def test_numwatchers(self):
        msg = make_message("numwatchers")
        resp = self.cli.call(msg)
        self.assertTrue(resp.get("numwatchers") >= 1)

    def test_numprocesses(self):
        msg = make_message("numprocesses")
        resp = self.cli.call(msg)
        self.assertTrue(resp.get("numprocesses") >= 1)

    def test_processes(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        before = len(resp.get('pids'))

        msg2 = make_message("incr", name="test")
        self.cli.call(msg2)

        resp = self.cli.call(msg1)
        self.assertEqual(len(resp.get('pids')), before + 1)

        self.cli.send_message("incr", name="test", nb=2)
        resp = self.cli.call(msg1)
        self.assertEqual(len(resp.get('pids')), before + 3)

    def test_watchers(self):
        if 'TRAVIS' in os.environ:
            return
        resp = self.cli.call(make_message("list"))
        self.assertTrue(len(resp.get('watchers')) > 0)

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

    def test_add_watcher(self):
        msg = make_message("add", name="test_add_watcher",
                           cmd=self._get_cmd(),
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

    def test_add_watcher_arbiter_stopped(self):
        # stop the arbiter
        resp = self.cli.call(make_message("stop"))
        self.assertEqual(resp.get("status"), "ok")

        msg = make_message("add", name="add_watcher_arbiter_stopped",
                           cmd=self._get_cmd(),
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

        # start it back
        resp = self.cli.call(make_message("start"))
        self.assertEqual(resp.get("status"), "ok")

    def test_add_watcher1(self):
        resp = self.cli.call(make_message("list"))
        before = resp.get('watchers')
        before.sort()

        msg = make_message("add", name="add_watcher1",
                           cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(make_message("list"))
        after = resp.get('watchers')
        self.assertEqual(len(before) + 1, len(after))
        self.assertTrue("add_watcher1" in after)
        self.assertFalse("add_watcher1" in before)

    def test_add_watcher2(self):
        resp = self.cli.call(make_message("numwatchers"))
        before = resp.get("numwatchers")

        msg = make_message("add", name="add_watcher2", cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(make_message("numwatchers"))
        self.assertEqual(resp.get("numwatchers"), before + 1)

    def test_add_watcher3(self):
        msg = make_message("add", name="add_watcher3", cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(msg)
        self.assertTrue(resp.get('status'), 'error')

    def test_add_watcher4(self):
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name="add_watcher4", cmd=cmd, args=args,
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

    def test_add_watcher5(self):
        cmd, args = self._get_cmd_args()
        name = "add_watcher5"
        msg = make_message("add", name=name, cmd=cmd, args=args,
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")
        resp = self.cli.call(make_message("start", name=name))
        self.assertEqual(resp.get("status"), "ok")
        resp = self.cli.call(make_message("status", name=name))
        self.assertEqual(resp.get("status"), "active")

    def test_add_watcher6(self):
        cmd, args = self._get_cmd_args()
        name = "add_watcher6"
        msg = make_message("add", name=name, cmd=cmd, args=args,
                           start=True, options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

        resp = self.cli.call(make_message("status", name=name))
        self.assertEqual(resp.get("status"), "active")

    def test_add_watcher7(self):
        cmd, args = self._get_cmd_args()
        name = "add_watcher7"
        msg = make_message("add", name=name, cmd=cmd, args=args, start=True,
                           options=self._get_options(flapping_window=100))
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

        resp = self.cli.call(make_message("status", name=name))
        self.assertEqual(resp.get("status"), "active")

        resp = self.cli.call(make_message("options", name=name))
        options = resp.get('options', {})
        self.assertEqual(options.get("flapping_window"), 100)

    def test_rm_watcher(self):
        resp = self.cli.call(make_message("numwatchers"))
        before = resp.get("numwatchers")
        name = "rm_watcher"
        msg = make_message("add", name=name, cmd=self._get_cmd(),
                           options=self._get_options())
        self.cli.call(msg)
        resp = self.cli.call(make_message("numwatchers"))
        self.assertEqual(resp.get("numwatchers"), before + 1)

        msg = make_message("rm", name=name)
        self.cli.call(msg)
        resp = self.cli.call(make_message("numwatchers"))
        self.assertEqual(resp.get("numwatchers"), before)

    def _test_stop(self):
        resp = self.cli.call(make_message("quit"))
        self.assertEqual(resp.get("status"), "ok")
        self.assertRaises(CallError, self.cli.call, make_message("list"))

        self._stop_runners()
        cli = CircusClient()
        dummy_process = 'circus.tests.support.run_process'
        self.test_file = self._run_circus(dummy_process)
        msg = make_message("numprocesses")
        resp = cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")

    def test_reload(self):
        resp = self.cli.call(make_message("reload"))
        self.assertEqual(resp.get("status"), "ok")

    def test_reload1(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        processes1 = resp.get('pids')

        truncate_file(self.test_file)  # clean slate
        self.cli.call(make_message("reload"))
        self.assertTrue(poll_for(self.test_file, 'START'))  # restarted

        msg2 = make_message("list", name="test")
        resp = self.cli.call(msg2)
        processes2 = resp.get('pids')

        self.assertNotEqual(processes1, processes2)

    def test_reload2(self):
        msg1 = make_message("list", name="test")
        resp = self.cli.call(msg1)
        processes1 = resp.get('pids')
        before = len(processes1)

        truncate_file(self.test_file)  # clean slate
        self.cli.call(make_message("reload"))
        self.assertTrue(poll_for(self.test_file, 'START'))  # restarted

        make_message("list", name="test")
        resp = self.cli.call(msg1)

        processes2 = resp.get('pids')
        self.assertEqual(len(processes2), before)
        self.assertNotEqual(processes1[0], processes2[0])

    def test_stop_watchers(self):
        if 'TRAVIS' in os.environ:
            return
        resp = self.cli.call(make_message("stop"))
        self.assertEqual(resp.get("status"), "ok")

    def test_stop_watchers1(self):
        if 'TRAVIS' in os.environ:
            return
        self.cli.call(make_message("stop", async=False))
        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get("status"), "stopped")

    def test_stop_watchers2(self):
        if 'TRAVIS' in os.environ:
            return
        self.cli.call(make_message("stop", name="test", async=False))
        resp = self.cli.call(make_message("status", name="test"))
        self.assertEqual(resp.get('status'), "stopped")

    def test_stop_watchers3(self):
        if 'TRAVIS' in os.environ:
            return

        name = "stop_watchers3"
        cmd, args = self._get_cmd_args()
        msg = make_message("add", name=name,
                           cmd=cmd, args=args,
                           options=self._get_options())
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("status"), "ok")
        self.cli.call(make_message("start", name=name))

        def _status():
            resp = self.cli.call(make_message("status", name=name))
            return resp.get('status')

        self.assertEqual(_status(), "active")

        resp = self.cli.call(make_message("start", name=name))
        self.assertEqual(resp.get("status"), "ok")

        self.cli.call(make_message("stop", name=name))
        resp = self.cli.call(make_message("status", name=name))
        self.assertEqual(resp.get('status'), "stopped")
        self.assertEqual(_status(), "stopped")


class TestTrainer(unittest.TestCase, _TestTrainer):
    @classmethod
    def setUpClass(cls):
        _TestTrainer.setUpClass()

    @classmethod
    def tearDownClass(cls):
        _TestTrainer.tearDownClass()


class TestUDP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setUpClass(cls)

    @classmethod
    def tearDownClass(cls):
        _tearDownClass(cls)

    def test_udp_discovery(self):
        if 'TRAVIS' in os.environ:
            return

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


class TestSingleton(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _setUpClass(cls, singleton=True)

    @classmethod
    def tearDownClass(cls):
        _tearDownClass(cls)

    def test_singleton(self):
        # adding more than one process should fail
        res = self.cli.send_message('incr', name='test')
        self.assertEqual(res['numprocesses'], 1)


class TestPlugin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fd, cls.datafile = mkstemp()
        os.close(fd)
        plugin = 'circus.tests.test_arbiter.Plugin'
        plugins = [{'use': plugin, 'file': cls.datafile}]
        _setUpClass(cls, plugins=plugins)

    @classmethod
    def tearDownClass(cls):
        _tearDownClass(cls)

    def test_plugins(self):
        # doing a few operations
        def nb_processes():
            return len(self.cli.send_message('list', name='test').get('pids'))

        def incr_processes():
            return self.cli.send_message('incr', name='test')

        # wait for the plugin to be started
        self.assertTrue(poll_for(self.datafile, 'PLUGIN STARTED'))

        self.assertEqual(nb_processes(), 1)
        incr_processes()
        self.assertEqual(nb_processes(), 2)

        # wait for the plugin to receive the signal
        self.assertTrue(poll_for(self.datafile, 'test:spawn'))
        truncate_file(self.datafile)
        incr_processes()
        self.assertEqual(nb_processes(), 3)
        # wait for the plugin to receive the signal
        self.assertTrue(poll_for(self.datafile, 'test:spawn'))


class MockWatcher(Watcher):

    def start(self):
        self.started = True


class TestArbiter(unittest.TestCase):
    """
    Unit tests for the arbiter class to codify requirements within
    behavior.
    """
    @classmethod
    def setUpClass(cls):
        _setUpClass(cls, singleton=True)

    @classmethod
    def tearDownClass(cls):
        _tearDownClass(cls)

    def test_start_watcher(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1)
        self.arb.start_watcher(watcher)
        self.assertTrue(watcher.started)

    def test_start_watchers_with_autostart(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        self.arb.start_watcher(watcher)
        self.assertFalse(getattr(watcher, 'started', False))

    def test_start_watchers_warmup_delay(self):
        watcher = MockWatcher(name='foo', cmd='serve', priority=1)
        arbiter = self.arb

        with patch('circus.arbiter.sleep') as mock_sleep:
            arbiter.start_watcher(watcher)
            mock_sleep.assert_called_with(0)

        # now make sure we don't sleep when there is a autostart
        watcher = MockWatcher(name='foo', cmd='serve', priority=1,
                              autostart=False)
        with patch('circus.arbiter.sleep') as mock_sleep:
            arbiter.start_watcher(watcher)
            assert not mock_sleep.called

    def test_add_watcher(self):
        watcher = self.arb.add_watcher('foo', 'sleep 5')
        self.arb.start_watcher(watcher)
        self.assertEqual(watcher.status(), 'active')
