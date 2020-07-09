import signal
import sys
import os
import time
import warnings
try:
    import queue as Queue
except ImportError:
    import Queue  # NOQA
try:
    from test.support import captured_output
except ImportError:
    try:
        from test.test_support import captured_output  # NOQA
    except ImportError:
        captured_output = None  # NOQA

import tornado
from unittest import mock

from circus import logger
from circus.process import RUNNING, UNEXISTING

from circus.stream import QueueStream
from circus.tests.support import TestCircus, truncate_file
from circus.tests.support import async_poll_for, EasyTestSuite
from circus.tests.support import MagicMockFuture, skipIf, IS_WINDOWS
from circus.tests.support import PYTHON
from circus.util import get_python_version, tornado_sleep, to_str
from circus.watcher import Watcher

if hasattr(signal, 'SIGKILL'):
    SIGKILL = signal.SIGKILL
else:
    SIGKILL = signal.SIGTERM

warnings.filterwarnings('ignore',
                        module='threading', message='sys.exc_clear')


class FakeProcess(object):

    def __init__(self, pid, status, started=1, age=1):
        self.status = status
        self.pid = pid
        self.started = started
        self.age = age
        self.stopping = False

    def returncode(self):
        return 0

    def children(self, **kwargs):
        return []

    def is_alive(self):
        return True

    def stop(self):
        pass

    def wait(self, *args, **kwargs):
        pass


class TestWatcher(TestCircus):

    runner = None

    @tornado.testing.gen_test
    def test_decr_too_much(self):
        yield self.start_arbiter()
        res = yield self.numprocesses('decr', name='test', nb=100)
        self.assertEqual(res, 0)
        res = yield self.numprocesses('decr', name='test', nb=100)
        self.assertEqual(res, 0)
        res = yield self.numprocesses('incr', name='test', nb=1)
        self.assertEqual(res, 1)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_signal(self):
        yield self.start_arbiter(check_delay=1.0)
        resp = yield self.numprocesses('incr', name='test')
        self.assertEqual(resp, 2)
        # wait for both to have started
        resp = yield async_poll_for(self.test_file, 'STARTSTART')
        self.assertTrue(resp)
        truncate_file(self.test_file)

        pids = yield self.pids()
        self.assertEqual(len(pids), 2)
        to_kill = pids[0]
        status = yield self.status('signal', name='test', pid=to_kill,
                                   signum=SIGKILL)
        self.assertEqual(status, 'ok')

        # make sure the process is restarted
        res = yield async_poll_for(self.test_file, 'START')
        self.assertTrue(res)

        # we still should have two processes, but not the same pids for them
        pids = yield self.pids()
        count = 0
        while len(pids) < 2 and count < 10:
            pids = yield self.pids()
            time.sleep(.1)
        self.assertEqual(len(pids), 2)
        self.assertTrue(to_kill not in pids)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_unexisting(self):
        yield self.start_arbiter()
        watcher = self.arbiter.get_watcher("test")

        to_kill = []
        nb_proc = len(watcher.processes)

        for process in list(watcher.processes.values()):
            to_kill.append(process.pid)
            # the process is killed in an unsual way
            process.stop()
            # and wait for it to die
            process.wait(3)

            # ensure the old process is considered "unexisting"
            self.assertEqual(process.status, UNEXISTING)

        # this should clean up and create a new process
        yield watcher.reap_and_manage_processes()

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

        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_stats(self):
        yield self.start_arbiter()
        resp = yield self.call("stats")
        self.assertTrue("test" in resp.get('infos'))
        watchers = resp.get('infos')['test']

        self.assertEqual(watchers[list(watchers.keys())[0]]['cmdline'].lower(),
                         PYTHON.split(os.sep)[-1].lower())
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_max_age(self):
        yield self.start_arbiter()
        # let's run 15 processes
        yield self.numprocesses('incr', name='test', nb=14)
        initial_pids = yield self.pids()

        # we want to make sure the watcher is really up and running 14
        # processes, and stable
        yield async_poll_for(self.test_file, 'START' * 15)
        truncate_file(self.test_file)  # make sure we have a clean slate

        # we want a max age of 1 sec.
        options = {'max_age': 1, 'max_age_variance': 0}
        result = yield self.call('set', name='test', waiting=True,
                                 options=options)

        self.assertEqual(result.get('status'), 'ok')

        current_pids = yield self.pids()
        self.assertEqual(len(current_pids), 15)
        self.assertNotEqual(initial_pids, current_pids)
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_arbiter_reference(self):
        yield self.start_arbiter()
        self.assertEqual(self.arbiter.watchers[0].arbiter,
                         self.arbiter)
        yield self.stop_arbiter()


class TestWatcherInitialization(TestCircus):

    @tornado.testing.gen_test
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

    @tornado.testing.gen_test
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

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_copy_path(self):
        watcher = SomeWatcher(stream=True)
        yield watcher.run()
        # wait for watcher data at most 5s
        messages = []
        resp = False
        start_time = time.time()
        while (time.time() - start_time) <= 5:
            yield tornado_sleep(0.5)
            # More than one Queue.get call is needed to get full
            # output from a watcher in an environment with rich sys.path.
            try:
                m = watcher.stream.get(block=False)
                messages.append(m)
            except Queue.Empty:
                pass
            data = ''.join(to_str(m['data']) for m in messages)
            if 'XYZ' in data:
                resp = True
                break
        self.assertTrue(resp)
        yield watcher.stop()

    @skipIf(IS_WINDOWS, "virtualenv not supported yet on Windows")
    @tornado.testing.gen_test
    def test_venv(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        yield watcher.run()
        try:
            py_version = get_python_version()
            major = py_version[0]
            minor = py_version[1]
            wanted = os.path.join(venv, 'lib', 'python%d.%d' % (major, minor),
                                  'site-packages')
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            yield watcher.stop()
        self.assertTrue(wanted in ppath)

    @skipIf(IS_WINDOWS, "virtualenv not supported yet on Windows")
    @tornado.testing.gen_test
    def test_venv_site_packages(self):
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        watcher = SomeWatcher(virtualenv=venv)
        yield watcher.run()
        try:
            yield tornado_sleep(1)
            py_version = get_python_version()
            major = py_version[0]
            minor = py_version[1]
            wanted = os.path.join(venv, 'lib', 'python%d.%d' % (major, minor),
                                  'site-packages')
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            yield watcher.stop()

        self.assertTrue(wanted in ppath.split(os.pathsep))

    @skipIf(IS_WINDOWS, "virtualenv not supported yet on Windows")
    @tornado.testing.gen_test
    def test_venv_py_ver(self):
        py_ver = "my_py_ver"
        venv = os.path.join(os.path.dirname(__file__), 'venv')
        wanted = os.path.join(venv, 'lib', 'python%s' % py_ver,
                              'site-packages')
        if not os.path.exists(wanted):
            os.makedirs(wanted)
        watcher = SomeWatcher(virtualenv=venv, virtualenv_py_ver=py_ver)
        yield watcher.run()
        try:
            yield tornado_sleep(1)
            ppath = watcher.watcher.env['PYTHONPATH']
        finally:
            yield watcher.stop()

        self.assertTrue(wanted in ppath.split(os.pathsep))


class SomeWatcher(object):

    def __init__(self, stream=False, loop=None, **kw):
        if stream:
            self.stream = QueueStream()
        else:
            self.stream = None
        self.watcher = None
        self.kw = kw
        if loop is None:
            self.loop = tornado.ioloop.IOLoop.current()
        else:
            self.loop = loop

    @tornado.gen.coroutine
    def run(self):
        if self.stream:
            qstream = {'stream': self.stream}
        else:
            qstream = None

        old_environ = os.environ
        old_paths = sys.path[:]
        try:
            sys.path = ['XYZ']
            os.environ = {'COCONUTS': 'MIGRATE'}
            cmd = ('%s -c "import sys; '
                   'sys.stdout.write(\':\'.join(sys.path)); '
                   ' sys.stdout.flush()"') % PYTHON

            self.watcher = Watcher('xx', cmd, copy_env=True, copy_path=True,
                                   stdout_stream=qstream, loop=self.loop,
                                   **self.kw)
            yield self.watcher.start()
        finally:
            os.environ = old_environ
            sys.path[:] = old_paths

    @tornado.gen.coroutine
    def stop(self):
        if self.watcher is not None:
            yield self.watcher.stop()


SUCCESS = 1
FAILURE = 2
ERROR = 3


class TestWatcherHooks(TestCircus):

    def run_with_hooks(self, hooks, streams=False):
        if streams:
            self.stream = QueueStream()
            self.errstream = QueueStream()
            stdout_stream = {'stream': self.stream}
            stderr_stream = {'stream': self.errstream}
        else:
            self.stream = None
            self.errstream = None
            stdout_stream = None
            stderr_stream = None

        dummy_process = 'circus.tests.support.run_process'
        return self._create_circus(dummy_process,
                                   stdout_stream=stdout_stream,
                                   stderr_stream=stderr_stream,
                                   hooks=hooks, debug=True, use_async=True)

    @tornado.gen.coroutine
    def _stop(self):
        yield self.call("stop", name="test", waiting=True)

    @tornado.gen.coroutine
    def _stats(self):
        yield self.call("stats", name="test")

    @tornado.gen.coroutine
    def _extended_stats(self):
        yield self.call("stats", name="test", extended=True)

    @tornado.gen.coroutine
    def get_status(self):
        resp = yield self.call("status", name="test")
        raise tornado.gen.Return(resp['status'])

    def test_missing_hook(self):
        hooks = {'before_start': ('fake.hook.path', False)}
        self.assertRaises(ImportError, self.run_with_hooks, hooks)

    @tornado.gen.coroutine
    def _test_hooks(self, hook_name='before_start', status='active',
                    behavior=SUCCESS, call=None,
                    hook_kwargs_test_function=None):
        events = {'before_start_called': False}

        def hook(watcher, arbiter, hook_name, **kwargs):
            events['%s_called' % hook_name] = True
            events['arbiter_in_hook'] = arbiter

            if hook_kwargs_test_function is not None:
                hook_kwargs_test_function(kwargs)

            if hook_name == 'extended_stats':
                kwargs['stats']['tx'] = 1000
                return
            if behavior == SUCCESS:
                return True
            elif behavior == FAILURE:
                return False

            raise TypeError('beeeuuua')

        old = logger.exception
        logger.exception = lambda x: x

        hooks = {hook_name: (hook, False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        yield arbiter.start()
        try:
            if call:
                yield call()
            resp_status = yield self.get_status()
            self.assertEqual(resp_status, status)
        finally:
            yield arbiter.stop()
            logger.exception = old

        self.assertTrue(events['%s_called' % hook_name])
        self.assertEqual(events['arbiter_in_hook'], arbiter)

    @tornado.gen.coroutine
    def _test_extended_stats(self, extended=False):
        events = {'extended_stats_called': False}

        def hook(watcher, arbiter, hook_name, **kwargs):
            events['extended_stats_called'] = True

        old = logger.exception
        logger.exception = lambda x: x

        hooks = {'extended_stats': (hook, False)}
        testfile, arbiter = self.run_with_hooks(hooks)
        yield arbiter.start()
        try:
            if extended:
                yield self._extended_stats()
            else:
                yield self._stats()
            resp_status = yield self.get_status()
            self.assertEqual(resp_status, 'active')
        finally:
            yield arbiter.stop()
            logger.exception = old

        self.assertEqual(events['extended_stats_called'], extended)

    @tornado.testing.gen_test
    def test_before_start(self):
        yield self._test_hooks()

    @tornado.testing.gen_test
    def test_before_start_fails(self):
        yield self._test_hooks(behavior=ERROR, status='stopped')

    @tornado.testing.gen_test
    def test_before_start_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_start')

    @tornado.testing.gen_test
    def test_after_start(self):
        yield self._test_hooks(hook_name='after_start')

    @tornado.testing.gen_test
    def test_after_start_fails(self):
        if captured_output:
            with captured_output('stderr'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='after_start')

    @tornado.testing.gen_test
    def test_after_start_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_start')

    @tornado.testing.gen_test
    def test_before_stop(self):
        yield self._test_hooks(hook_name='before_stop', status='stopped',
                               call=self._stop)

    def _hook_signal_kwargs_test_function(self, kwargs):
        self.assertTrue("pid" not in kwargs)
        self.assertTrue("signum" not in kwargs)
        self.assertTrue(kwargs["pid"] in (signal.SIGTERM, SIGKILL))
        self.assertTrue(int(kwargs["signum"]) > 1)

    @tornado.testing.gen_test
    def test_before_signal(self):
        func = self._hook_signal_kwargs_test_function
        yield self._test_hooks(hook_name='before_signal', status='stopped',
                               call=self._stop,
                               hook_kwargs_test_function=func)

    @tornado.testing.gen_test
    def test_after_signal(self):
        func = self._hook_signal_kwargs_test_function
        yield self._test_hooks(hook_name='after_signal', status='stopped',
                               call=self._stop,
                               hook_kwargs_test_function=func)

    @tornado.testing.gen_test
    def test_before_stop_fails(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='before_stop',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_before_stop_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='before_stop', call=self._stop)

    @tornado.testing.gen_test
    def test_after_stop(self):
        yield self._test_hooks(hook_name='after_stop', status='stopped',
                               call=self._stop)

    @tornado.testing.gen_test
    def test_after_stop_fails(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='after_stop',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_after_stop_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_stop', call=self._stop)

    @tornado.testing.gen_test
    def test_before_spawn(self):
        yield self._test_hooks(hook_name='before_spawn')

    @tornado.testing.gen_test
    def test_before_spawn_failure(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='before_spawn',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_before_spawn_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='before_spawn', call=self._stop)

    @tornado.testing.gen_test
    def test_after_spawn(self):
        yield self._test_hooks(hook_name='after_spawn')

    @tornado.testing.gen_test
    def test_after_spawn_failure(self):
        if captured_output:
            with captured_output('stdout'):
                yield self._test_hooks(behavior=ERROR, status='stopped',
                                       hook_name='after_spawn',
                                       call=self._stop)

    @tornado.testing.gen_test
    def test_after_spawn_false(self):
        yield self._test_hooks(behavior=FAILURE, status='stopped',
                               hook_name='after_spawn', call=self._stop)

    def _hook_before_reap_kwargs_test_function(self, kwargs):
        self.assertIn('process_pid', kwargs)
        self.assertIn('time', kwargs)

    @tornado.testing.gen_test
    def test_before_reap(self):
        func = self._hook_before_reap_kwargs_test_function
        yield self._test_hooks(hook_name='before_reap',
                               hook_kwargs_test_function=func)

    def _hook_after_reap_kwargs_test_function(self, kwargs):
        self.assertIn('process_pid', kwargs)
        self.assertIn('time', kwargs)
        self.assertEqual(-15, kwargs['exit_code'])
        # process_status is None because process is stopped by circus
        self.assertIsNone(kwargs['process_status'])

    @tornado.testing.gen_test
    def test_after_reap(self):
        func = self._hook_after_reap_kwargs_test_function
        yield self._test_hooks(hook_name='after_reap',
                               hook_kwargs_test_function=func)

    @tornado.testing.gen_test
    def test_extended_stats(self):
        yield self._test_extended_stats()
        yield self._test_extended_stats(extended=True)


def oneshot_process(test_file):
    pass


class RespawnTest(TestCircus):

    @tornado.testing.gen_test
    def test_not_respawning(self):
        oneshot_process = 'circus.tests.test_watcher.oneshot_process'
        testfile, arbiter = self._create_circus(oneshot_process,
                                                respawn=False, use_async=True)
        yield arbiter.start()
        watcher = arbiter.watchers[-1]
        try:
            # Per default, we shouldn't respawn processes,
            # so we should have one process, even if in a dead state.
            resp = yield self.call("numprocesses", name="test")
            self.assertEqual(resp['numprocesses'], 1)

            # let's reap processes and explicitely ask for process management
            yield watcher.reap_and_manage_processes()

            # we should have zero processes (the process shouldn't respawn)
            self.assertEqual(len(watcher.processes), 0)

            # If we explicitely ask the watcher to respawn its processes,
            # ensure it's doing so.
            yield watcher.start()
            self.assertEqual(len(watcher.processes), 1)
        finally:
            yield arbiter.stop()

    @tornado.testing.gen_test
    def test_stopping_a_watcher_doesnt_spawn(self):
        watcher = Watcher("foo", "foobar", respawn=True, numprocesses=3,
                          graceful_timeout=0)
        watcher._status = "started"

        watcher.spawn_processes = MagicMockFuture()
        watcher.send_signal = mock.MagicMock()

        # We have one running process and a dead one.
        watcher.processes = {1234: FakeProcess(1234, status=RUNNING),
                             1235: FakeProcess(1235, status=RUNNING)}

        # When we call manage_process(), the watcher should try to spawn a new
        # process since we aim to have 3 of them.
        yield watcher.manage_processes()
        self.assertTrue(watcher.spawn_processes.called)
        # Now, we want to stop everything.
        watcher.processes = {1234: FakeProcess(1234, status=RUNNING),
                             1235: FakeProcess(1235, status=RUNNING)}
        watcher.spawn_processes.reset_mock()
        yield watcher.stop()
        yield watcher.manage_processes()
        # And be sure we don't spawn new processes in the meantime.
        self.assertFalse(watcher.spawn_processes.called)


test_suite = EasyTestSuite(__name__)
