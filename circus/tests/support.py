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
import socket
try:
    import sysconfig
    DEBUG = sysconfig.get_config_var('Py_DEBUG') == 1
except ImportError:
    # py2.6, we don't really care about that flage here
    # since no one will run Python --with-pydebug in 2.6
    DEBUG = 0

try:
    from unittest import skip, skipIf, TestCase, TestSuite, findTestCases
except ImportError:
    from unittest2 import skip, skipIf, TestCase, TestSuite  # NOQA
    from unittest2 import findTestCases  # NOQA

from tornado.testing import AsyncTestCase
from zmq.eventloop import ioloop
import mock
import tornado

from circus import get_arbiter
from circus.util import DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB
from circus.util import tornado_sleep, ConflictError
from circus.client import AsyncCircusClient, make_message
from circus.stream import QueueStream

ioloop.install()
if 'ASYNC_TEST_TIMEOUT' not in os.environ:
    os.environ['ASYNC_TEST_TIMEOUT'] = '30'


class EasyTestSuite(TestSuite):
    def __init__(self, name):
        try:
            super(EasyTestSuite, self).__init__(
                findTestCases(sys.modules[name]))
        except KeyError:
            pass


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


def get_ioloop():
    from zmq.eventloop.ioloop import ZMQPoller
    from zmq.eventloop.ioloop import ZMQError, ETERM
    from tornado.ioloop import PollIOLoop

    class DebugPoller(ZMQPoller):
        def __init__(self):
            super(DebugPoller, self).__init__()
            self._fds = []

        def register(self, fd, events):
            if fd not in self._fds:
                self._fds.append(fd)
            return self._poller.register(fd, self._map_events(events))

        def modify(self, fd, events):
            if fd not in self._fds:
                self._fds.append(fd)
            return self._poller.modify(fd, self._map_events(events))

        def unregister(self, fd):
            if fd in self._fds:
                self._fds.remove(fd)
            return self._poller.unregister(fd)

        def poll(self, timeout):
            """
            #737 - For some reason the poller issues events with
            unexistant FDs, usually with big ints. We have not found yet the
            reason of this
            behavior that happens only during the tests. But by filtering out
            those events, everything works fine.

            """
            z_events = self._poller.poll(1000*timeout)
            return [(fd, self._remap_events(evt)) for fd, evt in z_events
                    if fd in self._fds]

    class DebugLoop(PollIOLoop):
        def initialize(self, **kwargs):
            PollIOLoop.initialize(self, impl=DebugPoller(), **kwargs)

        def handle_callback_exception(self, callback):
            exc_type, exc_value, tb = sys.exc_info()
            raise exc_value

        @staticmethod
        def instance():
            PollIOLoop.configure(DebugLoop)
            return PollIOLoop.instance()

        def start(self):
            try:
                super(DebugLoop, self).start()
            except ZMQError as e:
                if e.errno == ETERM:
                    # quietly return on ETERM
                    pass
                else:
                    raise e

    from tornado import ioloop
    ioloop.IOLoop.configure(DebugLoop)
    return ioloop.IOLoop.instance()


def get_available_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("", 0))
        return s.getsockname()[1]
    finally:
        s.close()


class TestCircus(AsyncTestCase):

    arbiter_factory = get_arbiter
    arbiters = []

    def setUp(self):
        super(TestCircus, self).setUp()
        self.files = []
        self.dirs = []
        self.tmpfiles = []
        self._clients = {}
        self.plugins = []

    @property
    def cli(self):
        if self.arbiters == []:
            # nothing is running
            raise Exception("nothing is running")

        endpoint = self.arbiters[-1].endpoint
        if endpoint in self._clients:
            return self._clients[endpoint]

        cli = AsyncCircusClient(endpoint=endpoint)
        self._clients[endpoint] = cli
        return cli

    def _stop_clients(self):
        for client in self._clients.values():
            client.stop()
        self._clients.clear()

    def get_new_ioloop(self):
        return get_ioloop()

    def tearDown(self):
        for file in self.files + self.tmpfiles:
            if os.path.exists(file):
                os.remove(file)
        for dir in self.dirs:
            shutil.rmtree(dir)

        self._stop_clients()

        for plugin in self.plugins:
            plugin.stop()

        for arbiter in self.arbiters:
            if arbiter.running:
                try:
                    arbiter.stop()
                except ConflictError:
                    pass

        self.arbiters = []
        super(TestCircus, self).tearDown()

    def make_plugin(self, klass, endpoint=DEFAULT_ENDPOINT_DEALER,
                    sub=DEFAULT_ENDPOINT_SUB, check_delay=1,
                    **config):
        config['active'] = True
        plugin = klass(endpoint, sub, check_delay, None, **config)
        self.plugins.append(plugin)
        return plugin

    @tornado.gen.coroutine
    def start_arbiter(self, cmd='circus.tests.support.run_process',
                      stdout_stream=None, debug=True, **kw):
        if stdout_stream is None:
            self.stream = QueueStream()
            stdout_stream = {'stream': self.stream}
        testfile, arbiter = self._create_circus(
            cmd, stdout_stream=stdout_stream,
            debug=debug, async=True, **kw)
        self.test_file = testfile
        self.arbiter = arbiter
        self.arbiters.append(arbiter)
        yield self.arbiter.start()

    @tornado.gen.coroutine
    def stop_arbiter(self):
        for watcher in self.arbiter.iter_watchers():
            yield self.arbiter.rm_watcher(watcher.name)
        yield self.arbiter._emergency_stop()

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
    def _create_circus(cls, callable_path, plugins=None, stats=False,
                       async=False, arbiter_kw=None, **kw):
        resolve_name(callable_path)   # used to check the callable
        fd, testfile = mkstemp()
        os.close(fd)
        wdir = os.path.dirname(__file__)
        args = ['generic.py', callable_path, testfile]
        worker = {'cmd': _CMD, 'args': args, 'working_dir': wdir,
                  'name': 'test', 'graceful_timeout': 2}
        worker.update(kw)
        if not arbiter_kw:
            arbiter_kw = {}
        debug = arbiter_kw['debug'] = kw.get('debug',
                                             arbiter_kw.get('debug', False))
        # -1 => no periodic callback to manage_watchers by default
        arbiter_kw['check_delay'] = kw.get('check_delay',
                                           arbiter_kw.get('check_delay', -1))

        _gp = get_available_port
        arbiter_kw['controller'] = "tcp://127.0.0.1:%d" % _gp()
        arbiter_kw['pubsub_endpoint'] = "tcp://127.0.0.1:%d" % _gp()
        arbiter_kw['multicast_endpoint'] = "udp://237.219.251.97:12027"

        if stats:
            arbiter_kw['statsd'] = True
            arbiter_kw['stats_endpoint'] = "tcp://127.0.0.1:%d" % _gp()
            arbiter_kw['statsd_close_outputs'] = not debug

        if async:
            arbiter_kw['background'] = False
            arbiter_kw['loop'] = get_ioloop()
        else:
            arbiter_kw['background'] = True

        arbiter = cls.arbiter_factory([worker], plugins=plugins, **arbiter_kw)
        cls.arbiters.append(arbiter)
        return testfile, arbiter

    def _run_circus(self, callable_path, plugins=None, stats=False, **kw):

        testfile, arbiter = TestCircus._create_circus(callable_path,
                                                      plugins, stats, **kw)
        self.arbiters.append(arbiter)
        self.files.append(testfile)
        return testfile

    @tornado.gen.coroutine
    def _stop_runners(self):
        for arbiter in self.arbiters:
            yield arbiter.stop()
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


def has_circusweb():
    try:
        import circusweb       # NOQA
        return True
    except ImportError:
        return False


class TimeoutException(Exception):
    pass


def poll_for_callable(func, *args, **kwargs):
    """Replay to update the status during timeout seconds."""
    timeout = 5

    if 'timeout' in kwargs:
        timeout = kwargs.pop('timeout')

    start = time()
    last_exception = None
    while time() - start < timeout:
        try:
            func_args = []
            for arg in args:
                if callable(arg):
                    func_args.append(arg())
                else:
                    func_args.append(arg)
            func(*func_args)
        except AssertionError as e:
            last_exception = e
            sleep(0.1)
        else:
            return True
    raise last_exception or AssertionError('No exception triggered yet')


def poll_for(filename, needles, timeout=5):
    """Poll a file for a given string.

    Raises a TimeoutException if the string isn't found after timeout seconds
    of polling.

    """
    if isinstance(needles, str):
        needles = [needles]

    start = time()
    needle = content = None
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
    needle = content = None
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


def run_plugin(klass, config, plugin_info_callback=None, duration=300,
               endpoint=DEFAULT_ENDPOINT_DEALER,
               pubsub_endpoint=DEFAULT_ENDPOINT_SUB):
    check_delay = 1
    ssh_server = None

    class _Statsd(object):
        gauges = []
        increments = defaultdict(int)

        def gauge(self, name, value):
            self.gauges.append((name, value))

        def increment(self, name):
            self.increments[name] += 1

        def stop(self):
            pass

    _statsd = _Statsd()
    plugin = klass(endpoint, pubsub_endpoint, check_delay, ssh_server,
                   **config)

    # make sure we close the existing statsd client
    if hasattr(plugin, 'statsd'):
        plugin.statsd.stop()

    plugin.statsd = _statsd

    deadline = time() + (duration / 1000.)
    plugin.loop.add_timeout(deadline, plugin.stop)

    plugin.start()
    try:
        if plugin_info_callback:
            plugin_info_callback(plugin)
    finally:
        plugin.stop()

    return _statsd


@tornado.gen.coroutine
def async_run_plugin(klass, config, plugin_info_callback, duration=300,
                     endpoint=DEFAULT_ENDPOINT_DEALER,
                     pubsub_endpoint=DEFAULT_ENDPOINT_SUB):
    queue = multiprocessing.Queue()
    plugin_info_callback = functools.partial(plugin_info_callback, queue)
    circusctl_process = multiprocessing.Process(
        target=run_plugin,
        args=(klass, config, plugin_info_callback, duration,
              endpoint, pubsub_endpoint))
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
