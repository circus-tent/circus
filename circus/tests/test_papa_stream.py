import time
import sys
import os
import tempfile
import tornado
import random

from circus.util import papa
from circus.client import make_message
from circus.tests.support import TestCircus, async_poll_for, truncate_file
from circus.tests.support import EasyTestSuite, skipIf, IS_WINDOWS
from circus.stream import FileStream, WatchedFileStream
from circus.stream import TimedRotatingFileStream


def run_process(testfile, *args, **kw):
    try:
        # print once, then wait
        sys.stdout.write('stdout')
        sys.stdout.flush()
        sys.stderr.write('stderr')
        sys.stderr.flush()
        with open(testfile, 'a+') as f:
            f.write('START')
        time.sleep(1.)
    except:  # noqa: E722
        return 1


@skipIf(papa is None, "papa not available")
@skipIf('TRAVIS' in os.environ, "Skipped on Travis")
class TestPapaStream(TestCircus):
    dummy_process = 'circus.tests.test_stream.run_process'
    papa_port = random.randint(20000, 30000)

    def setUp(self):
        super(TestPapaStream, self).setUp()
        papa.set_debug_mode(quit_when_connection_closed=True)
        papa.set_default_port(self.papa_port)
        papa.set_default_connection_timeout(120)
        fd, self.stdout = tempfile.mkstemp()
        os.close(fd)
        fd, self.stderr = tempfile.mkstemp()
        os.close(fd)
        self.stdout_stream = FileStream(self.stdout)
        self.stderr_stream = FileStream(self.stderr)
        self.stdout_arg = {'stream': self.stdout_stream}
        self.stderr_arg = {'stream': self.stderr_stream}

    def tearDown(self):
        self.stdout_stream.close()
        self.stderr_stream.close()
        if os.path.exists(self.stdout):
            os.remove(self.stdout)
        if os.path.exists(self.stderr):
            os.remove(self.stderr)

    @tornado.gen.coroutine
    def _start_arbiter(self):
        yield self.start_arbiter(cmd=self.dummy_process,
                                 stdout_stream=self.stdout_arg,
                                 stderr_stream=self.stderr_arg,
                                 use_papa=True)

    @tornado.gen.coroutine
    def restart_arbiter(self):
        yield self.arbiter.restart()

    @tornado.gen.coroutine
    def call(self, _cmd, **props):
        msg = make_message(_cmd, **props)
        resp = yield self.cli.call(msg)
        raise tornado.gen.Return(resp)

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_file_stream(self):
        yield self._start_arbiter()
        stream = FileStream(self.stdout, max_bytes='12', backup_count='3')
        self.assertTrue(isinstance(stream._max_bytes, int))
        self.assertTrue(isinstance(stream._backup_count, int))
        yield self.stop_arbiter()
        stream.close()

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_watched_file_stream(self):
        yield self._start_arbiter()
        stream = WatchedFileStream(self.stdout,
                                   time_format='%Y-%m-%d %H:%M:%S')
        self.assertTrue(isinstance(stream._time_format, str))
        yield self.stop_arbiter()
        stream.close()

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_timed_rotating_file_stream(self):
        yield self._start_arbiter()
        stream = TimedRotatingFileStream(self.stdout,
                                         rotate_when='H',
                                         rotate_interval='5',
                                         backup_count='3',
                                         utc='True')
        self.assertTrue(isinstance(stream._interval, int))
        self.assertTrue(isinstance(stream._backup_count, int))
        self.assertTrue(isinstance(stream._utc, bool))
        self.assertTrue(stream._suffix is not None)
        self.assertTrue(stream._ext_match is not None)
        self.assertTrue(stream._rollover_at > 0)
        yield self.stop_arbiter()
        stream.close()

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_stream(self):
        yield self._start_arbiter()
        # wait for the process to be started
        res1 = yield async_poll_for(self.stdout, 'stdout')
        res2 = yield async_poll_for(self.stderr, 'stderr')
        self.assertTrue(res1)
        self.assertTrue(res2)

        # clean slate
        truncate_file(self.stdout)
        truncate_file(self.stderr)

        # restart and make sure streams are still working
        yield self.restart_arbiter()

        # wait for the process to be restarted
        res1 = yield async_poll_for(self.stdout, 'stdout')
        res2 = yield async_poll_for(self.stderr, 'stderr')
        self.assertTrue(res1)
        self.assertTrue(res2)
        yield self.stop_arbiter()


test_suite = EasyTestSuite(__name__)
