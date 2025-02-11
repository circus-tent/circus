import io
import time
import sys
import os
import tempfile
import tornado

from datetime import datetime

from circus.client import make_message
from circus.tests.support import TestCircus, async_poll_for, truncate_file
from circus.tests.support import TestCase, EasyTestSuite, skipIf, IS_WINDOWS
from circus.stream import FileStream, WatchedFileStream
from circus.stream import TimedRotatingFileStream
from circus.stream import FancyStdoutStream


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


class TestWatcher(TestCircus):
    dummy_process = 'circus.tests.test_stream.run_process'

    def setUp(self):
        super(TestWatcher, self).setUp()
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
                                 stderr_stream=self.stderr_arg)

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

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_stop_and_restart(self):
        # cf https://github.com/circus-tent/circus/issues/912

        yield self._start_arbiter()
        # wait for the process to be started
        res1 = yield async_poll_for(self.stdout, 'stdout')
        res2 = yield async_poll_for(self.stderr, 'stderr')
        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertFalse(self.stdout_stream._file.closed)
        self.assertFalse(self.stderr_stream._file.closed)

        # clean slate
        truncate_file(self.stdout)
        truncate_file(self.stderr)

        # stop the watcher
        yield self.arbiter.watchers[0].stop()

        self.assertTrue(self.stdout_stream._file.closed)
        self.assertTrue(self.stderr_stream._file.closed)

        # start it again
        yield self.arbiter.watchers[0].start()

        # wait for the process to be restarted
        res1 = yield async_poll_for(self.stdout, 'stdout')
        res2 = yield async_poll_for(self.stderr, 'stderr')
        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertFalse(self.stdout_stream._file.closed)
        self.assertFalse(self.stderr_stream._file.closed)

        yield self.stop_arbiter()


class TestFancyStdoutStream(TestCase):

    def color_start(self, code):
        return '\033[0;3%s;40m' % code

    def color_end(self):
        return '\033[0m\n'

    def get_stream(self, *args, **kw):
        # need a constant timestamp
        now = datetime.now()
        stream = FancyStdoutStream(*args, **kw)

        # patch some details that will be used
        stream.out = io.StringIO()
        stream.now = lambda: now

        return stream

    def get_output(self, stream):
        # stub data
        data = {'data': 'hello world',
                'pid': 333}

        # get the output
        stream(data)
        output = stream.out.getvalue()
        stream.out.close()

        expected = self.color_start(stream.color_code)
        expected += stream.now().strftime(stream.time_format) + " "
        expected += "[333] | " + data['data'] + self.color_end()
        return output, expected

    def test_random_colored_output(self):
        stream = self.get_stream()
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_red_colored_output(self):
        stream = self.get_stream(color='red')
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_time_formatting(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    def test_data_split_into_lines(self):
        stream = self.get_stream(color='red')
        data = {'data': '\n'.join(['foo', 'bar', 'baz']),
                'pid': 333}

        stream(data)
        output = stream.out.getvalue()
        stream.out.close()

        # NOTE: We expect 4 b/c the last line needs to add a newline
        #       in order to prepare for the next chunk
        self.assertEqual(len(output.split('\n')), 4)

    def test_data_with_extra_lines(self):
        stream = self.get_stream(color='red')

        # There is an extra newline
        data = {'data': '\n'.join(['foo', 'bar', 'baz', '']),
                'pid': 333}

        stream(data)
        output = stream.out.getvalue()
        stream.out.close()

        self.assertEqual(len(output.split('\n')), 4)

    def test_color_selections(self):
        # The colors are chosen from an ordered list where each index
        # is used to calculate the ascii escape sequence.
        for i, color in enumerate(FancyStdoutStream.colors):
            stream = self.get_stream(color)
            self.assertEqual(i + 1, stream.color_code)
            stream.out.close()


class TestFileStream(TestCase):
    stream_class = FileStream

    def get_stream(self, *args, **kw):
        # need a constant timestamp
        now = datetime.now()
        stream = self.stream_class(*args, **kw)

        # patch some details that will be used
        stream._file.close()
        stream._file = io.StringIO()
        stream._open = lambda: stream._file
        stream.now = lambda: now

        return stream

    def get_output(self, stream):
        # stub data
        data = {'data': 'hello world',
                'pid': 333}

        # get the output
        stream(data)
        output = stream._file.getvalue()
        stream._file.close()

        expected = stream.now().strftime(stream._time_format) + " "
        expected += "[333] | " + data['data'] + '\n'
        return output, expected

    @skipIf(IS_WINDOWS and sys.version_info[0] < 3,
            "StringIO has no fileno on Python 2 and Windows")
    def test_time_formatting(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')
        output, expected = self.get_output(stream)
        self.assertEqual(output, expected)

    @skipIf(IS_WINDOWS and sys.version_info[0] < 3,
            "StringIO has no fileno on Python 2 and Windows")
    def test_data_split_into_lines(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')
        data = {'data': '\n'.join(['foo', 'bar', 'baz']),
                'pid': 333}

        stream(data)
        output = stream._file.getvalue()
        stream._file.close()

        # NOTE: We expect 4 b/c the last line needs to add a newline
        #       in order to prepare for the next chunk
        self.assertEqual(len(output.split('\n')), 4)

    @skipIf(IS_WINDOWS and sys.version_info[0] < 3,
            "StringIO has no fileno on Python 2 and Windows")
    def test_data_with_extra_lines(self):
        stream = self.get_stream(time_format='%Y/%m/%d %H.%M.%S')

        # There is an extra newline
        data = {'data': '\n'.join(['foo', 'bar', 'baz', '']),
                'pid': 333}

        stream(data)
        output = stream._file.getvalue()
        stream._file.close()
        self.assertEqual(len(output.split('\n')), 4)

    @skipIf(IS_WINDOWS and sys.version_info[0] < 3,
            "StringIO has no fileno on Python 2 and Windows")
    def test_data_with_no_EOL(self):
        stream = self.get_stream()

        # data with no newline and more than 1024 chars
        data = {'data': '*' * 1100, 'pid': 333}

        stream(data)
        stream(data)
        output = stream._file.getvalue()
        stream._file.close()

        self.assertEqual(output, '*' * 2200)


class TestWatchedFileStream(TestFileStream):
    stream_class = WatchedFileStream

    def get_real_stream(self, *args, **kw):
        # need a constant timestamp
        now = datetime.now()
        stream = self.stream_class(*args, **kw)
        stream.now = lambda: now
        return stream

    # we can't run this test on Windows due to file locking
    @skipIf(IS_WINDOWS, "On Windows")
    def test_move_file(self):
        _test_fd, test_filename = tempfile.mkstemp()
        stream = self.get_real_stream(filename=test_filename)

        line1_contents = 'line 1'
        line2_contents = 'line 2'
        file1 = test_filename + '.1'

        # write data, then move the file to simulate a log rotater that will
        # rename the file underneath us, then write more data to ensure that
        # logging continues to work after the rename
        stream({'data': line1_contents})
        os.rename(test_filename, file1)
        stream({'data': line2_contents})
        stream.close()

        with open(test_filename) as line2:
            self.assertEqual(line2.read().strip(), line2_contents)
        with open(file1) as line1:
            self.assertEqual(line1.read().strip(), line1_contents)

        os.unlink(test_filename)
        os.unlink(file1)


test_suite = EasyTestSuite(__name__)
