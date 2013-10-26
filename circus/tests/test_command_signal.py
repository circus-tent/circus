import sys
import time
import signal
import multiprocessing
import tornado

from circus.tests.support import TestCircus, EasyTestSuite, TimeoutException
from circus.client import AsyncCircusClient
from circus.stream import QueueStream, Empty
from circus.util import tornado_sleep
from zmq.utils.strtypes import u


exiting = False
channels = {0: [], 1: [], 2: [], 3: []}


def run_process(child_id, test_file=None):
    def send(msg):
        sys.stdout.write('{0}:{1}\n'.format(child_id, msg))
        sys.stdout.flush()

    names = {}
    signals = "HUP QUIT INT TERM USR1 USR2".split()
    exit_signals = set("INT TERM".split())
    children = []

    if not isinstance(child_id, int):
        child_id = 0
        for i in range(3):
            p = multiprocessing.Process(target=run_process, args=(i + 1,))
            p.daemon = True
            p.start()
            children.append(p)

    def callback(sig, frame=None):
        global exiting
        name = names[sig]
        send(name)
        if name in exit_signals:
            exiting = True

    for signal_name in signals:
        signum = getattr(signal, "SIG%s" % signal_name)
        names[signum] = signal_name
        signal.signal(signum, callback)

    send('STARTED')
    while not exiting:
        signal.pause()
    send('EXITING')


@tornado.gen.coroutine
def read_from_stream(stream, desired_channel, timeout=5):
    start = time.time()
    accumulator = ''
    while not channels[desired_channel] and time.time() - start < timeout:
        try:
            data = stream.get_nowait()
            data = u(data['data']).split('\n')
            accumulator += data.pop(0)
            if data:
                data.insert(0, accumulator)
                accumulator = data.pop()
                for line in data:
                    if len(line) > 1 and line[1] == ':':
                        channel, string = line.partition(':')[::2]
                        channels[int(channel)].append(string)
        except Empty:
            yield tornado_sleep(0.1)
    if channels[desired_channel]:
        raise tornado.gen.Return(channels[desired_channel].pop(0))
    raise TimeoutException('Timeout reading queue')


class SignalCommandTest(TestCircus):

    @tornado.testing.gen_test
    def test_handler(self):
        stream = QueueStream()
        cmd = 'circus.tests.test_command_signal.run_process'
        stdout_stream = {'stream': stream}
        stderr_stream = {'stream': stream}
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream,
                                 stderr_stream=stderr_stream, stats=True,
                                 stop_signal=signal.SIGINT)
        # waiting for data to appear in the queue
        data = yield read_from_stream(stream, 0)
        self.assertEqual('STARTED', data)

        # waiting for children
        data = yield read_from_stream(stream, 3)
        self.assertEqual('STARTED', data)
        data = yield read_from_stream(stream, 2)
        self.assertEqual('STARTED', data)
        data = yield read_from_stream(stream, 1)
        self.assertEqual('STARTED', data)

        # checking that our system is live and running
        client = AsyncCircusClient()
        res = yield client.send_message('list')
        watchers = sorted(res['watchers'])
        self.assertEqual(['circusd-stats', 'test'], watchers)

        # send USR1 to parent only
        res = yield client.send_message('signal', name='test', signum='usr1')
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'USR1')

        # send USR2 to children only
        res = yield client.send_message('signal', name='test', signum='usr2',
                                        children=True)
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'USR2')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'USR2')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'USR2')

        # send HUP to parent and children
        res = yield client.send_message('signal', name='test', signum='hup',
                                        recursive=True)
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'HUP')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'HUP')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'HUP')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'HUP')

        # stop process
        res = yield client.send_message('stop', name='test')
        self.assertEqual(res['status'], 'ok')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'INT')
        res = yield read_from_stream(stream, 0)
        self.assertEqual(res, 'EXITING')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'TERM')
        res = yield read_from_stream(stream, 1)
        self.assertEqual(res, 'EXITING')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'TERM')
        res = yield read_from_stream(stream, 2)
        self.assertEqual(res, 'EXITING')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'TERM')
        res = yield read_from_stream(stream, 3)
        self.assertEqual(res, 'EXITING')

        timeout = time.time() + 5
        stopped = False
        while time.time() < timeout:
            res = yield client.send_message('status', name='test')
            if res['status'] == 'stopped':
                stopped = True
                break
            self.assertEqual(res['status'], 'stopping')
        self.assertTrue(stopped)

        yield self.stop_arbiter()

test_suite = EasyTestSuite(__name__)

if __name__ == '__main__':
    run_process(*sys.argv)
