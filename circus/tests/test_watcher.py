import signal
import sys
import os
import threading
import time
import warnings
import logging

import mock
from zmq.eventloop import ioloop
from zmq.utils.strtypes import u

from circus import logger
from circus.process import RUNNING, UNEXISTING

from circus.stream import QueueStream
from circus.tests.support import TestCircus, ifSupportsSetUpClass, poll_for, truncate_file
from circus.util import get_python_version
from circus.watcher import Watcher

try:
    from test.support import captured_output
except ImportError:
    from test.test_support import captured_output

warnings.filterwarnings('ignore',
                        module='threading', message='sys.exc_clear')


class FakeProcess(object):

    def __init__(self, pid, status, started=1, age=1):
        self.status = status
        self.pid = pid
        self.started = started
        self.age = age


@ifSupportsSetUpClass
class TestWatcher(TestCircus):

    runner = None

    @classmethod
    def setUpClass(cls):
        dummy_process = 'circus.tests.support.run_process'
        cls.stream = QueueStream()
        testfile, arbiter = cls._create_circus(
            dummy_process, stdout_stream={'stream': cls.stream},
            debug=True)
        cls.arbiter = arbiter
        cls.test_file = testfile
        poll_for(testfile, 'START')

    @classmethod
    def tearDownClass(cls):
        cls.arbiter.stop()

    def tearDown(self):
        super(TestCircus, self).tearDown()
        current = self.numprocesses('numprocesses')
        if current > 1:
            self.numprocesses('decr', name='test', nb=current-1)

    def status(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('status')

    def numprocesses(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numprocesses')

    def pids(self):
        return self.call('list', name='test').get('pids')

    def test_decr_too_much(self):
        res = self.numprocesses('decr', name='test', nb=100)
        self.assertEqual(res, 0)
        res = self.numprocesses('decr', name='test', nb=100)
        self.assertEqual(res, 0)
        res = self.numprocesses('incr', name='test', nb=1)
        self.assertEqual(res, 1)

    def test_signal(self):
        self.assertEqual(self.numprocesses('incr', name='test'), 2)
        # wait for both to have started
        self.assertTrue(poll_for(self.test_file, 'STARTSTART'))
        truncate_file(self.test_file)

        pids = self.pids()
        self.assertEqual(len(pids), 2)
        to_kill = pids[0]
        self.assertEqual(self.status('signal', name='test', pid=to_kill,
                                      signum=signal.SIGKILL), 'ok')

        # make sure the process is restarted
        self.assertTrue(poll_for(self.test_file, 'START'))

        # we still should have two processes, but not the same pids for them
        pids = self.pids()
        count = 0
        while len(pids) < 2 and count < 10:
            pids = self.pids()
            time.sleep(.1)
        self.assertEqual(len(pids), 2)
        self.assertTrue(to_kill not in pids)

    def test_unexisting(self):
        # may cause an exception in tornado ioloop so mask it
        logging.getLogger('tornado.application').setLevel(logging.CRITICAL)
        watcher = self.arbiter.get_watcher("test")

        to_kill = []
        nb_proc = len(watcher.processes)

        for process in list(watcher.processes.values()):
            to_kill.append(process.pid)
            # the process is killed in an unsual way
            try:
                # use SIGKILL instead of SIGSEGV so we don't get 'app crashed' dialogs on OS X
                os.kill(process.pid, signal.SIGKILL)
            except OSError:
                pass

            # and wait for it to die
            try:
                pid, status = os.waitpid(process.pid, 0)
            except OSError:
                pass

            # ansure the old process is considered "unexisting"
            self.assertEqual(process.status, UNEXISTING)

        # this should clean up and create a new process
        watcher.reap_and_manage_processes()

        # watcher ids should have been reused
        wids = [p.wid for p in watcher.processes.values()]
        self.assertEqual(max(wids), watcher.numprocesses)
        self.assertEqual(sum(wids), sum(range(1, watcher.numprocesses + 1)))

        # we should have a new process here now
        self.assertEqual(len(watcher.processes), nb_proc)
        for p in watcher.processes.values():
            # and that one needs to have a new pid.
            self.assertFalse(p.pid in to_kill)

            # and should not be unexisting...
            self.assertNotEqual(p.status, UNEXISTING)

    def test_stats(self):
        resp = self.call("stats").get('infos')
        self.assertTrue("test" in resp)
        watchers = resp['test']

        self.assertEqual(watchers[list(watchers.keys())[0]]['cmdline'].lower(),
                         sys.executable.split(os.sep)[-1].lower())

    def test_max_age(self):
        # let's run 15 processes
        self.numprocesses('incr', name='test', nb=14)
        initial_pids = self.pids()

        # we want to make sure the watcher is really up and running 14
        # processes, and stable
        poll_for(self.test_file, 'START' * 15)
        truncate_file(self.test_file)  # make sure we have a clean slate

        # we want a max age of 1 sec.
        result = self.call('set', name='test',
                           options={'max_age': 1, 'max_age_variance': 0})

        self.assertEqual(result.get('status'), 'ok')

        # we want to wait for all 15 processes to restart
        ready = False

        def _ready(olds, news):
            for pid in olds:
                if pid in news:
                    return False
            return True

        started = time.time()
        while not ready:
            if time.time() - started > 10.:
                break
            time.sleep(.1)
            ready = _ready(initial_pids, self.pids())

        current_pids = self.pids()
        self.assertEqual(len(current_pids), 15)
        self.assertNotEqual(initial_pids, current_pids)

    def test_arbiter_reference(self):
        self.assertEqual(self.arbiter.watchers[0].arbiter,
                         self.arbiter)


class TestWatcherInitialization(TestCircus):

    def test_copy_env(self):
        old_environ = os.environ
        try:
            os.environ = {'COCONUTS': 'MIGRATE'}
            watcher = Watcher("foo", "foobar", copy_env=True)
            self.assertEqual(watcher.env, os.environ)

            watcher = Watcher("foo", "foobar", copy_env=True,
                              env={"AWESOMENESS": "YES"})
            self.assertEqual(watcher.env,
                              {'COCONUTS': 'MIGRATE', 'AWESOMENESS': 'YES'})
        finally:
            os.environ = old_environ

    def test_hook_in_PYTHON_PATH(self):
        # we have a hook in PYTHONPATH
        tempdir = self.get_tmpdir()

        hook = 'def hook(*args, **kw):\n    return True\n'
        with open(os.path.join(tempdir, 'plugins.py'), 'w') as f:
            f.write(hook)

        old_environ = os.environ
        try:
            os.environ = {'PYTHONPATH': tempdir}
            hooks = {'before_start': ('plugins.hook', False)}

            watcher = Watcher("foo", "foobar", copy_env=True, hooks=hooks)

            self.assertEqual(watcher.env, os.environ)
        finally:
            os.environ = old_environ

    def test_copy_path(self):
        watcher = SomeWatcher()
        watcher.start()
        # wait for watcher data at most 5s
        data = watcher.stream.get(timeout=5)
        watcher.stop()
        data = u(data['data'])
        self.assertTrue('XYZ' in data, data)

    def test_venv(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        watcher.start()
        try:
            time.sleep(.1)
            py_version = get_python_version()
            major = py_version[0]
            minor = py_version[1]
            wanted = os.path.join(venv, 'lib', 'python%d.%d' % (major, minor),
                                  'site-packages',
                                  'pip-7.7-py%d.%d.egg' % (major, minor))
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            watcher.stop()
        self.assertTrue(wanted in ppath)

    def test_venv_site_packages(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        watcher.start()
        try:
            time.sleep(.1)
            py_version = get_python_version()
            major = py_version[0]
            minor = py_version[1]
            wanted = os.path.join(venv, 'lib', 'python%d.%d' % (major, minor),
                                  'site-packages')
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            watcher.stop()

        self.assertTrue(wanted in ppath.split(os.pathsep))


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

            self.loop = ioloop.IOLoop()
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
        self.errstream = QueueStream()
        dummy_process = 'circus.tests.support.run_process'
        return self._create_circus(dummy_process,
                                   stdout_stream={'stream': self.stream},
                                   stderr_stream={'stream': self.errstream},
                                   hooks=hooks)

    def _stop(self):
        self.call("stop", name="test", async=False)

    def get_status(self):
        return self.call("status", name="test")['status']

    def test_missing_hook(self):
        hooks = {'before_start': ('fake.hook.path', False)}
        self.assertRaises(ImportError, self.run_with_hooks, hooks)

    def _test_hooks(self, hook_name='before_start', status='active',
                    behavior=SUCCESS, call=None,
                    hook_kwargs_test_function=None):
        events = {'before_start_called': False}

        def hook(watcher, arbiter, hook_name, **kwargs):
            events['before_start_called'] = True
            events['arbiter_in_hook'] = arbiter

            if hook_kwargs_test_function is not None:
                hook_kwargs_test_function(kwargs)

            if behavior == SUCCESS:
                return True
            elif behavior == FAILURE:
                return False

            raise TypeError('beeeuuua')

        old = logger.exception
        logger.exception = lambda x: x

        hooks = {hook_name: (hook, False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        try:
            if call:
                call()
            self.assertEqual(self.get_status(), status)
        finally:
            arbiter.stop()
            logger.exception = old

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
        with captured_output('stderr'):
            self._test_hooks(behavior=ERROR, status='stopped',
                             hook_name='after_start')

    def test_after_start_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='after_start')

    def test_before_stop(self):
        self._test_hooks(hook_name='before_stop', status='stopped',
                         call=self._stop)

    def _hook_signal_kwargs_test_function(self, kwargs):
        self.assertTrue("pid" not in kwargs)
        self.assertTrue("signum" not in kwargs)
        self.assertTrue(kwargs["pid"] in (signal.SIGTERM, signal.SIGKILL))
        self.assertTrue(int(kwargs["signum"]) > 1)

    def test_before_signal(self):
        func = self._hook_signal_kwargs_test_function
        self._test_hooks(hook_name='before_signal', status='stopped',
                         call=self._stop,
                         hook_kwargs_test_function=func)

    def test_after_signal(self):
        func = self._hook_signal_kwargs_test_function
        self._test_hooks(hook_name='after_signal', status='stopped',
                         call=self._stop,
                         hook_kwargs_test_function=func)

    def test_before_stop_fails(self):
        with captured_output('stdout'):
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
        with captured_output('stdout'):
            self._test_hooks(behavior=ERROR, status='stopped',
                             hook_name='after_stop',
                             call=self._stop)

    def test_after_stop_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='after_stop', call=self._stop)

    def test_before_spawn(self):
        self._test_hooks(hook_name='before_spawn')

    def test_before_spawn_failure(self):
        with captured_output('stdout'):
            self._test_hooks(behavior=ERROR, status='stopped',
                             hook_name='before_spawn',
                             call=self._stop)

    def test_before_spawn_false(self):
        self._test_hooks(behavior=FAILURE, status='stopped',
                         hook_name='before_spawn', call=self._stop)


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
            self.assertEqual(resp['numprocesses'], 1)

            # let's reap processes and explicitely ask for process management
            watcher.reap_and_manage_processes()

            # we should have zero processes (the process shouldn't respawn)
            self.assertEqual(len(watcher.processes), 0)

            # If we explicitely ask the watcher to respawn its processes,
            # ensure it's doing so.
            watcher.spawn_processes()
            self.assertEqual(len(watcher.processes), 1)
        finally:
            arbiter.stop()

    def test_stopping_a_watcher_doesnt_spawn(self):
        watcher = Watcher("foo", "foobar", respawn=True, numprocesses=3)
        watcher.stopped = False

        watcher.spawn_processes = mock.MagicMock()
        watcher.loop = mock.MagicMock()
        watcher.send_signal = mock.MagicMock()

        # We have one running process and a dead one.
        watcher.processes = {1234: FakeProcess(1234, status=RUNNING),
                             1235: FakeProcess(1235, status=RUNNING)}

        # When we call manage_process(), the watcher should try to spawn a new
        # process since we aim to have 3 of them.
        watcher.manage_processes()
        self.assertTrue(watcher.spawn_processes.called)

        # Now, we want to stop everything.
        watcher.processes = {1234: FakeProcess(1234, status=RUNNING),
                             1235: FakeProcess(1235, status=RUNNING)}
        watcher.spawn_processes.reset_mock()
        watcher.stop()
        watcher.manage_processes()

        # And be sure we don't spawn new processes in the meantime.
        self.assertFalse(watcher.spawn_processes.called)
