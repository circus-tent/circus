import sys
import tornado
import time
import socket

from circus.tests.support import TestCircus, TimeoutException
from circus.tests.support import skipIf, IS_WINDOWS
from circus.stream import QueueStream, Empty
from circus.util import tornado_sleep
from zmq.utils.strtypes import u
from circus.sockets import CircusSocket


def run_process(test_file):
    # get stdin socket and output bound address
    sock = socket.fromfd(0, socket.AF_INET, socket.SOCK_STREAM)
    hostaddr, port = sock.getsockname()
    sys.stdout.write("%s %s" % (hostaddr, port))
    return 1


@tornado.gen.coroutine
def read_from_stream(stream, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            data = stream.get_nowait()
            raise tornado.gen.Return(u(data['data']))
        except Empty:
            yield tornado_sleep(.1)
    raise TimeoutException('Timeout reading queue')


class StdinSocketTest(TestCircus):

    def setUp(self):
        super(StdinSocketTest, self).setUp()

    def tearDown(self):
        super(StdinSocketTest, self).tearDown()

    @skipIf(IS_WINDOWS, "Stdin socket not supported")
    @tornado.testing.gen_test
    def test_stdin_socket(self):
        cmd = 'circus.tests.test_stdin_socket.run_process'
        stream = QueueStream()
        stdout_stream = {'stream': stream}
        sk = CircusSocket(name='test', host='localhost', port=0)
        yield self.start_arbiter(cmd=cmd, stdout_stream=stdout_stream,
                                 arbiter_kw={'sockets': [sk]},
                                 stdin_socket='test', use_sockets=True)

        # check same socket in child fd 0
        addr_string_actual = yield read_from_stream(stream)
        addr_string_expected = "%s %s" % (sk.host, sk.port)
        self.assertEqual(addr_string_actual, addr_string_expected)

        yield self.stop_arbiter()

    @skipIf(IS_WINDOWS, "Stdin socket not supported")
    @tornado.testing.gen_test
    def test_stdin_socket_missing_raises(self):
        raised = False
        try:
            # expecting exception for no such socket
            yield self.start_arbiter(stdin_socket='test')
        except Exception:
            raised = True
        self.assertTrue(raised)

        yield self.stop_arbiter()
