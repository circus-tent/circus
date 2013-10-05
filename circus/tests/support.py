from tempfile import mkstemp, mkdtemp
import os
import signal
import sys
from time import time, sleep
from collections import defaultdict
import cProfile
import pstats
import shutil
import functools
import multiprocessing

from tornado.testing import AsyncTestCase
from zmq.eventloop import ioloop
import mock
import tornado

from circus import get_arbiter
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                         DEFAULT_ENDPOINT_STATS)
from circus.util import tornado_sleep
from circus.client import AsyncCircusClient, make_message
from circus.stream import QueueStream


def resolve_name(name):
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    last_exc = None

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError as exc:
            last_exc = exc
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            if last_exc is not None:
                raise last_exc
            raise ImportError(name)

    if ret is None:
        if last_exc is not None:
            raise last_exc
        raise ImportError(name)

    return ret


_CMD = sys.executable


class TestCircus(AsyncTestCase):

    arbiter_factory = get_arbiter

    def setUp(self):
        ioloop.install()
        super(TestCircus, self).setUp()
        self.arbiters = []
        self.files = []
        self.dirs = []
        self.tmpfiles = []
        self.cli = AsyncCircusClient()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop().instance()

    def tearDown(self):
        self._stop_runners()
        for file in self.files + self.tmpfiles:
            if os.path.exists(file):
                os.remove(file)

        for dir in self.dirs:
            shutil.rmtree(dir)
        self.cli.stop()
        super(TestCircus, self).tearDown()

    @tornado.gen.coroutine
    def start_arbiter(self, cmd='circus.tests.support.run_process'):
        self.stream = QueueStream()
        testfile, arbiter = self._create_circus(
            cmd, stdout_stream={'stream': self.stream},
            debug=True, async=True)
        self.test_file = testfile
        self.arbiter = arbiter
        yield self.arbiter.start()

    @tornado.gen.coroutine
    def stop_arbiter(self):
        for watcher in self.arbiter.iter_watchers():
            self.arbiter.rm_watcher(watcher)
        yield self.arbiter.stop()

    @tornado.gen.coroutine
    def status(self, cmd, **props):
        resp = yield self.call(cmd, **props)
        raise tornado.gen.Return(resp.get('status'))

    @tornado.gen.coroutine
    def numwatchers(self, cmd, **props):
        resp = yield self.call(cmd, waiting=True, **props)
        raise tornado.gen.Return(resp.get('numprocesses'))

    @tornado.gen.coroutine
    def numprocesses(self, cmd, **props):
        resp = yield self.call(cmd, waiting=True, **props)
        raise tornado.gen.Return(resp.get('numprocesses'))

    @tornado.gen.coroutine
    def pids(self):
        resp = yield self.call('list', name='test')
        raise tornado.gen.Return(resp.get('pids'))

    def get_tmpdir(self):
        dir_ = mkdtemp()
        self.dirs.append(dir_)
        return dir_

    def get_tmpfile(self, content=None):
        fd, file = mkstemp()
        os.close(fd)
        self.tmpfiles.append(file)
        if content is not None:
            with open(file, 'w') as f:
                f.write(content)
        return file

    @classmethod
    def _create_circus(cls, callable, plugins=None, stats=False, async=False, **kw):
        resolve_name(callable)   # used to check the callable
        fd, testfile = mkstemp()
        os.close(fd)
        wdir = os.path.dirname(__file__)
        args = ['generic.py', callable, testfile]
        worker = {'cmd': _CMD, 'args': args, 'working_dir': wdir,
                  'name': 'test', 'graceful_timeout': 2}
        worker.update(kw)
        debug = kw.get('debug', False)

        fact = cls.arbiter_factory
        if async:
            arbiter = fact([worker], background=False, plugins=plugins,
                           debug=debug, loop=tornado.ioloop.IOLoop().instance())
        else:
            if stats:
                arbiter = fact([worker], background=True, plugins=plugins,
                               stats_endpoint=DEFAULT_ENDPOINT_STATS,
                            statsd=True,
                            debug=debug, statsd_close_outputs=not debug)
            else:
                arbiter = fact([worker], background=True, plugins=plugins,
                            debug=debug)
        #arbiter.start()
        return testfile, arbiter

    def _run_circus(self, callable, plugins=None, stats=False, **kw):

        testfile, arbiter = TestCircus._create_circus(callable, plugins, stats,
                                                      **kw)
        self.arbiters.append(arbiter)
        self.files.append(testfile)
        return testfile

    def _stop_runners(self):
        for arbiter in self.arbiters:
            arbiter.stop()
        self.arbiters = []

    @tornado.gen.coroutine
    def call(self, _cmd, **props):
        msg = make_message(_cmd, **props)
        resp = yield self.cli.call(msg)
        raise tornado.gen.Return(resp)


def profile(func):
    """Can be used to dump profile stats"""
    def _profile(*args, **kw):
        profiler = cProfile.Profile()
        try:
            return profiler.runcall(func, *args, **kw)
        finally:
            pstats.Stats(profiler).sort_stats('time').print_stats(30)
    return _profile


class Process(object):

    def __init__(self, testfile):
        self.testfile = testfile
        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def _write(self, msg):
        with open(self.testfile, 'a+') as f:
            f.write(msg)

    def handle_quit(self, *args):
        self._write('QUIT')
        self.alive = False

    def handle_chld(self, *args):
        self._write('CHLD')
        return

    def run(self):
        self._write('START')
        while self.alive:
            sleep(0.1)
        self._write('STOP')


def run_process(test_file):
    process = Process(test_file)
    process.run()
    return 1


def has_gevent():
    try:
        import gevent       # NOQA
        return True
    except ImportError:
        return False


class TimeoutException(Exception):
    pass


def poll_for(filename, needles, timeout=5):
    """Poll a file for a given string.

    Raises a TimeoutException if the string isn't found after timeout seconds
    of polling.

    """
    if isinstance(needles, str):
        needles = [needles]

    start = time()
    while time() - start < timeout:
        with open(filename) as f:
            content = f.read()
        for needle in needles:
            if needle in content:
                return True
        # When using gevent this will make sure the redirector greenlets are
        # scheduled.
        sleep(0.1)
    raise TimeoutException('Timeout polling "%s" for "%s". Content: %s' % (
        filename, needle, content))


@tornado.gen.coroutine
def async_poll_for(filename, needles, timeout=5):
    """Async version of poll_for
    """
    if isinstance(needles, str):
        needles = [needles]

    start = time()
    while time() - start < timeout:
        with open(filename) as f:
            content = f.read()
        for needle in needles:
            if needle in content:
                raise tornado.gen.Return(True)
        yield tornado_sleep(0.1)
    raise TimeoutException('Timeout polling "%s" for "%s". Content: %s' % (
        filename, needle, content))


def truncate_file(filename):
    """Truncate a file (empty it)."""
    open(filename, 'w').close()  # opening as 'w' overwrites the file


def run_plugin(klass, config, plugin_info_callback=None, duration=300):
    endpoint = DEFAULT_ENDPOINT_DEALER
    pubsub_endpoint = DEFAULT_ENDPOINT_SUB
    check_delay = 1
    ssh_server = None

    class _Statsd(object):
        gauges = []
        increments = defaultdict(int)

        def gauge(self, name, value):
            self.gauges.append((name, value))

        def increment(self, name):
            self.increments[name] += 1

    _statsd = _Statsd()
    plugin = klass(endpoint, pubsub_endpoint, check_delay, ssh_server,
                   **config)
    plugin.statsd = _statsd

    deadline = time() + (duration / 1000.)
    plugin.loop.add_timeout(deadline, plugin.loop.stop)
    plugin.start()
    if plugin_info_callback:
        plugin_info_callback(plugin)
    return _statsd


@tornado.gen.coroutine
def async_run_plugin(klass, config, plugin_info_callback):
    queue = multiprocessing.Queue()
    plugin_info_callback = functools.partial(plugin_info_callback, queue)
    circusctl_process = multiprocessing.Process(
        target=run_plugin,
        args=(klass, config, plugin_info_callback))
    circusctl_process.start()
    while queue.empty():
        yield tornado_sleep(.1)
    result = queue.get()
    raise tornado.gen.Return(result)


class FakeProcess(object):

    def __init__(self, pid, status, started=1, age=1):
        self.status = status
        self.pid = pid
        self.started = started
        self.age = age
        self.stopping = False

    def is_alive(self):
        return True

    def stop(self):
        pass


class MagicMockFuture(mock.MagicMock, tornado.concurrent.Future):

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def running(self):
        return False

    def done(self):
        return True

    def result(self, timeout=None):
        return None

    def exception(self, timeout=None):
        return None

    def add_done_callback(self, fn):
        fn(self)

    def set_result(self, result):
        pass

    def set_exception(self, exception):
        pass
