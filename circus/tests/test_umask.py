import sys
import os
import tornado
import signal
import time

from circus.tests.support import TestCircus, EasyTestSuite, TimeoutException
from circus.tests.support import skipIf, IS_WINDOWS
from circus.stream import QueueStream, Empty
from circus.util import tornado_sleep
from zmq.utils.strtypes import u


class Process(object):

    def __init__(self, test_file):
        try:
            if os.path.isdir(test_file):
                os.removedirs(test_file)
            else:
                os.unlink(test_file)
        except OSError:
            pass
        else:
            os.makedirs(test_file)

        # init signal handling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        self.alive = True
        sys.stdout.write('Done')
        sys.stdout.flush()

    # noinspection PyUnusedLocal
    def handle_quit(self, *args):
        self.alive = False

    def run(self):
        while self.alive:
            time.sleep(0.1)


def run_process(test_file):
    process = Process(test_file)
    process.run()
    return 1


@tornado.gen.coroutine
def read_from_stream(stream, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            data = stream.get_nowait()
            raise tornado.gen.Return(u(data['data']))
        except Empty:
            yield tornado_sleep(0.1)
    raise TimeoutException('Timeout reading queue')


class UmaskTest(TestCircus):

    def setUp(self):
        super(UmaskTest, self).setUp()
        self.original_umask = os.umask(int('022', 8))

    def tearDown(self):
        super(UmaskTest, self).tearDown()
        dirname = self.test_file
        if os.path.isdir(dirname):
            os.removedirs(dirname)
        os.umask(self.original_umask)

    @tornado.gen.coroutine
    def _call(self, _cmd, **props):
        resp = yield self.call(_cmd, waiting=True, **props)
        raise tornado.gen.Return(resp)

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_inherited(self):
        cmd = 'circus.tests.test_umask.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream)

        res = yield read_from_stream(stream)
        self.assertEqual(res, 'Done')

        yield self.stop_arbiter()

        self.assertTrue(os.path.isdir(self.test_file))
        mode = oct(os.stat(self.test_file).st_mode)[-3:]
        self.assertEqual(mode, '755')

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_set_before_launch(self):
        os.umask(2)
        cmd = 'circus.tests.test_umask.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream)

        res = yield read_from_stream(stream)
        self.assertEqual(res, 'Done')

        yield self.stop_arbiter()

        self.assertTrue(os.path.isdir(self.test_file))
        mode = oct(os.stat(self.test_file).st_mode)[-3:]
        self.assertEqual(mode, '775')

    @skipIf(IS_WINDOWS, "Streams not supported")
    @tornado.testing.gen_test
    def test_set_by_arbiter(self):
        cmd = 'circus.tests.test_umask.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream,
                                 arbiter_kw={'umask': 0})

        res = yield read_from_stream(stream)
        self.assertEqual(res, 'Done')

        yield self.stop_arbiter()

        self.assertTrue(os.path.isdir(self.test_file))
        mode = oct(os.stat(self.test_file).st_mode)[-3:]
        self.assertEqual(mode, '777')


test_suite = EasyTestSuite(__name__)

if __name__ == '__main__':
    run_process(sys.argv[1])
