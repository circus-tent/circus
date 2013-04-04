import signal
import sys
import os
import threading
import time

from zmq.eventloop import ioloop

from circus.tests.support import TestCircus, poll_for, truncate_file
from circus.stream import QueueStream
from circus.watcher import Watcher
from circus.process import UNEXISTING


class TestWatcher(TestCircus):

    runner = None

    @classmethod
    def setUpClass(cls):
        dummy_process = 'circus.tests.support.run_process'
        cls.stream = QueueStream()
        testfile, arbiter = cls._create_circus(
            dummy_process, stdout_stream={'stream': cls.stream})
        cls.arbiter = arbiter
        cls.test_file = testfile

    @classmethod
    def tearDownClass(cls):
        cls.arbiter.stop()

    def status(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('status')

    def numprocesses(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numprocesses')

    def pids(self):
        return self.call('list', name='test').get('pids')

    def test_signal(self):
        self.assertEquals(self.numprocesses('incr', name='test'), 2)
        # wait for both to have started
        self.assertTrue(poll_for(self.test_file, 'STARTSTART'))
        truncate_file(self.test_file)

        pids = self.pids()
        self.assertEquals(len(pids), 2)
        to_kill = pids[0]
        self.assertEquals(self.status('signal', name='test', pid=to_kill,
                                      signum=signal.SIGKILL), 'ok')

        # make sure process is restarted
        self.assertTrue(poll_for(self.test_file, 'START'))

        # we still should have two processes, but not the same pids for them
        pids = self.pids()
        self.assertEquals(len(pids), 2)
        self.assertTrue(to_kill not in pids)

    def test_unexisting(self):
        watcher = self.arbiter.get_watcher("test")

        to_kill = []
        self.assertEquals(len(watcher.processes), 2)
        for process in watcher.processes.values():
            to_kill.append(process.pid)
            # the process is killed in an unsual way
            os.kill(process.pid, signal.SIGSEGV)
            # and wait for it to die
            try:
                pid, status = os.waitpid(process.pid, 0)
            except OSError:
                pass

            # ansure the old process is considered "unexisting"
            self.assertEquals(process.status, UNEXISTING)

        # this should clean up and create a new process
        watcher.reap_and_manage_processes()

        # we should have a new process here now
        self.assertEquals(len(watcher.processes), 2)
        for p in watcher.processes.values():
            # and that one needs to have a new pid.
            self.assertFalse(p.pid in to_kill)

            # and should not be unexisting...
            self.assertNotEqual(p.status, UNEXISTING)

    def test_stats(self):
        resp = self.call("stats").get('infos')
        self.assertTrue("test" in resp)
        watchers = resp['test']

        self.assertEqual(watchers[watchers.keys()[0]]['cmdline'],
                         sys.executable.split(os.sep)[-1])

    def test_max_age(self):
        result = self.call('set', name='test',
                           options={'max_age': 1, 'max_age_variance': 0})
        self.assertEquals(result.get('status'), 'ok')
        initial_pids = self.pids()

        truncate_file(self.test_file)  # make sure we have a clean slate
        # expect at least one restart (max_age and restart), in less than 5s
        self.assertTrue(poll_for(self.test_file, 'QUITSTART'))

        current_pids = self.pids()
        self.assertEqual(len(current_pids), 1)
        self.assertNotEqual(initial_pids, current_pids)

    def test_arbiter_reference(self):
        if 'TRAVIS' in os.environ:
            # XXX we need to find out why this fails on travis
            return
        self.assertEqual(self.arbiter.watchers[0].arbiter,
                         self.arbiter)


class TestWatcherInitialization(TestCircus):

    def test_copy_env(self):
        old_environ = os.environ
        try:
            os.environ = {'COCONUTS': 'MIGRATE'}
            watcher = Watcher("foo", "foobar", copy_env=True)
            self.assertEquals(watcher.env, os.environ)

            watcher = Watcher("foo", "foobar", copy_env=True,
                              env={"AWESOMENESS": "YES"})
            self.assertEquals(watcher.env,
                              {'COCONUTS': 'MIGRATE', 'AWESOMENESS': 'YES'})
        finally:
            os.environ = old_environ

    def test_copy_path(self):
        watcher = SomeWatcher()
        watcher.start()
        # wait for watcher data at most 5s
        data = watcher.stream.get(timeout=5)
        watcher.stop()
        data = [v for k, v in data.items()][1]
        data = ''.join(data)
        self.assertTrue('XYZ' in data, data)

    def test_venv(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        watcher.start()
        try:
            time.sleep(.1)
            minor = sys.version_info[1]
            wanted = os.path.join(venv, 'lib', 'python2.%d' % minor,
                                  'site-packages',
                                  'pip-7.7-py2.%d.egg' % minor)
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            watcher.stop()
        self.assertTrue(wanted in ppath)


class SomeWatcher(threading.Thread):

    def __init__(self, **kw):
        threading.Thread.__init__(self)
        self.stream = QueueStream()
        self.loop = self.watcher = None
        self.kw = kw

    def run(self):
        qstream = {'stream': self.stream}
        old_environ = os.environ
        old_paths = sys.path[:]
        try:
            sys.path = ['XYZ']
            os.environ = {'COCONUTS': 'MIGRATE'}
            cmd = ('%s -c "import sys; '
                   'sys.stdout.write(\':\'.join(sys.path)); '
                   ' sys.stdout.flush()"') % sys.executable

            self.loop = ioloop.IOLoop.instance()
            self.watcher = Watcher('xx', cmd, copy_env=True, copy_path=True,
                                   stdout_stream=qstream, loop=self.loop,
                                   **self.kw)
            self.watcher.start()
            self.loop.start()
        finally:
            os.environ = old_environ
            sys.path[:] = old_paths

    def stop(self):
        if self.loop is not None:
            self.loop.stop()
        if self.watcher is not None:
            self.watcher.stop()
        self.join()


SUCCESS = 1
FAILURE = 2
ERROR = 3


class TestWatcherHooks(TestCircus):

    def run_with_hooks(self, hooks):
        self.stream = QueueStream()
        dummy_process = 'circus.tests.support.run_process'
        return self._create_circus(dummy_process,
                                   stdout_stream={'stream': self.stream},
                                   hooks=hooks)

    def _stop(self):
        self.call("stop", name="test")

    def get_status(self):
        return self.call("status", name="test")['status']

    def test_missing_hook(self):
        hooks = {'before_start': ('fake.hook.path', False)}
        self.assertRaises(ImportError, self.run_with_hooks, hooks)

    def _test_hooks(self, hook_name='before_start', status='active',
                    behavior=SUCCESS, call=None):
        events = {'before_start_called': False}

        def hook(watcher, arbiter, hook_name):
            events['before_start_called'] = True
            events['arbiter_in_hook'] = arbiter

            if behavior == SUCCESS:
                return True
            elif behavior == FAILURE:
                return False

            raise TypeError('beeeuuua')

        hooks = {hook_name: (hook, False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        try:
            if call:
                call()
            self.assertEqual(self.get_status(), status)
        finally:
            arbiter.stop()

        self.assertTrue(events['before_start_called'])
        self.assertEqual(events['arbiter_in_hook'], arbiter)

    def test_before_start(self):
        self._test_hooks()

    def test_before_start_fails(self):
        self._test_hooks(behavior=ERROR, status='stopped')

    def test_before_start_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='after_start')

    def test_after_start(self):
        self._test_hooks(hook_name='after_start')

    def test_after_start_fails(self):
        self._test_hooks(behavior=ERROR, status='stopped',
                         hook_name='after_start')

    def test_after_start_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='after_start')

    def test_before_stop(self):
        self._test_hooks(hook_name='before_stop', status='stopped',
                         call=self._stop)

    def test_before_stop_fails(self):
        self._test_hooks(behavior=ERROR, status='stopped',
                         hook_name='before_stop',
                         call=self._stop)

    def test_before_stop_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='before_stop', call=self._stop)

    def test_after_stop(self):
        self._test_hooks(hook_name='after_stop', status='stopped',
                         call=self._stop)

    def test_after_stop_fails(self):
        self._test_hooks(behavior=ERROR, status='stopped',
                         hook_name='after_stop',
                         call=self._stop)

    def test_after_stop_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='after_stop', call=self._stop)


def oneshot_process(test_file):
    pass


class RespawnTest(TestCircus):
    def test_not_respawning(self):
        oneshot_process = 'circus.tests.test_watcher.oneshot_process'
        testfile, arbiter = self._create_circus(oneshot_process, respawn=False)
        watcher = arbiter.watchers[-1]
        try:
            # Per default, we shouldn't respawn processes,
            # so we should have one process, even if in a dead state.
            resp = self.call("numprocesses", name="test")
            self.assertEquals(resp['numprocesses'], 1)

            # let's reap processes and explicitely ask for process management
            watcher.reap_and_manage_processes()

            # we should have zero processes (the process shouldn't respawn)
            self.assertEquals(len(watcher.processes), 0)

            # If we explicitely ask the watcher to respawn its processes,
            # ensure it's doing so.
            watcher.spawn_processes()
            self.assertEquals(len(watcher.processes), 1)
        finally:
            arbiter.stop()
