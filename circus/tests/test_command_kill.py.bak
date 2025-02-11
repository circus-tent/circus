import sys
import time
import signal
import tornado
import tornado.gen

from circus.tests.support import TestCircus, TimeoutException
from circus.tests.support import skipIf, IS_WINDOWS
from circus.client import AsyncCircusClient
from circus.stream import QueueStream, Empty
from circus.util import tornado_sleep, to_str


def send(msg):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


def obedient_process(*args, **kwargs):
    """Waits for SIGINT and exits normally"""
    stopped = []

    def handler(sig, frame):
        send('SIGINT')
        stopped.append(1)

    signal.signal(signal.SIGINT, handler)

    send('STARTED')
    while not stopped:
        signal.pause()
    send('STOPPED')


def hanged_process(*args, **kwargs):
    """Ignores SIGINT signal"""
    def handler(sig, frame):
        send('SIGINT')
        # ignore

    signal.signal(signal.SIGINT, handler)

    send('STARTED')
    while True:
        signal.pause()
    send('STOPPED')


class StreamReader(object):
    def __init__(self, stream, timeout=5):
        self._stream = stream
        self._timeout = timeout
        self._buffer = []

    @tornado.gen.coroutine
    def read(self, timeout=None):
        timeout = timeout or self._timeout

        if self._buffer:
            raise tornado.gen.Return(self._buffer.pop(0))

        start = time.time()
        while time.time() - start < timeout:
            try:
                msg = self._stream.get_nowait()
                lines = [l for l in to_str(msg['data']).split('\n') if l]
                self._buffer.extend(lines)
                raise tornado.gen.Return(self._buffer.pop(0))
            except Empty:
                yield tornado_sleep(0.1)
        raise TimeoutException('Timeout reading queue')


class KillCommandTest(TestCircus):

    @skipIf(IS_WINDOWS, "Streams not supported")
    def setUp(self):
        super(KillCommandTest, self).setUp()
        self.stream = QueueStream()
        self.reader = StreamReader(self.stream)
        self._client = None

    def tearDown(self):
        self._client.stop()
        self.stream.close()

    @property
    def client(self):
        if not self._client:
            self._client = AsyncCircusClient(endpoint=self.arbiter.endpoint)
        return self._client

    @tornado.gen.coroutine
    def assertMessage(self, msg, timeout=5):
        try:
            actual = yield self.reader.read(timeout=timeout)
        except TimeoutException:
            raise AssertionError('Timeout while waiting for message: {}'
                                 .format(msg))

        self.assertEqual(actual, msg)

    @tornado.testing.gen_test
    def test_exits_within_graceful_timeout(self):
        yield self.start_arbiter(
            cmd='circus.tests.test_command_kill.obedient_process',
            stdout_stream={'stream': self.stream},
            stderr_stream={'stream': self.stream})

        yield self.assertMessage('STARTED')

        res = yield self.client.send_message(
            'kill', name='test', signum='sigint',
            graceful_timeout=0.1, waiting=True)
        self.assertEqual(res['status'], 'ok')

        yield self.assertMessage('SIGINT')
        yield self.assertMessage('STOPPED')
        yield self.stop_arbiter()

    @tornado.testing.gen_test
    def test_kills_after_graceful_timeout(self):
        yield self.start_arbiter(
            cmd='circus.tests.test_command_kill.hanged_process',
            stdout_stream={'stream': self.stream},
            stderr_stream={'stream': self.stream})

        yield self.assertMessage('STARTED')

        res = yield self.client.send_message(
            'kill', name='test', signum='sigint',
            graceful_timeout=0.1, waiting=True)
        self.assertEqual(res['status'], 'ok')

        yield self.assertMessage('SIGINT')
        yield self.stop_arbiter()
