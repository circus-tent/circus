from tempfile import mkstemp
import os
import signal
import sys
from time import time, sleep
from collections import defaultdict
import cProfile
import pstats

import unittest2 as unittest

from circus import get_arbiter
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                         DEFAULT_ENDPOINT_STATS)
from circus.client import CircusClient, make_message


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


class TestCircus(unittest.TestCase):

    def setUp(self):
        self.arbiters = []
        self.files = []
        self.tmpfiles = []
        self.cli = CircusClient()

    def tearDown(self):
        self._stop_runners()
        for file in self.files + self.tmpfiles:
            if os.path.exists(file):
                os.remove(file)
        self.cli.stop()

    def get_tmpfile(self, content=None):
        fd, file = mkstemp()
        os.close(fd)
        self.tmpfiles.append(file)
        if content is not None:
            with open(file, 'w') as f:
                f.write(content)
        return file

    @classmethod
    def _create_circus(cls, callable, plugins=None, stats=False, **kw):
        resolve_name(callable)   # used to check the callable
        fd, testfile = mkstemp()
        os.close(fd)
        wdir = os.path.dirname(__file__)
        args = ['generic.py', callable, testfile]
        worker = {'cmd': _CMD, 'args': args, 'working_dir': wdir,
                  'name': 'test', 'graceful_timeout': 4}
        worker.update(kw)
        debug = kw.get('debug', False)

        if stats:
            arbiter = get_arbiter([worker], background=True, plugins=plugins,
                                  stats_endpoint=DEFAULT_ENDPOINT_STATS,
                                  statsd=True,
                                  debug=debug, statsd_close_outputs=not debug)
        else:
            arbiter = get_arbiter([worker], background=True, plugins=plugins,
                                  debug=debug)
        arbiter.start()
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

    def call(self, cmd, **props):
        msg = make_message(cmd, **props)
        return self.cli.call(msg)


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
    while time() - start < 5:
        with open(filename) as f:
            content = f.read()
        for needle in needles:
            if needle in content:
                return True
        # When using gevent this will make sure the redirector greenlets are
        # scheduled.
        sleep(0)
    raise TimeoutException('Timeout polling "%s" for "%s". Content: %s' % (
        filename, needle, content))


def truncate_file(filename):
    """Truncate a file (empty it)."""
    open(filename, 'w').close()  # opening as 'w' overwrites the file


def run_plugin(klass, config, duration=300):
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
    return _statsd
