from circus.tests.support import TestCase, EasyTestSuite, get_ioloop
from circus.controller import Controller
from circus.util import DEFAULT_ENDPOINT_MULTICAST
from circus import logger
import circus.controller

from unittest import mock


class TestController(TestCase):

    def test_add_job(self):
        arbiter = mock.MagicMock()

        class MockedController(Controller):
            called = False

            def _init_stream(self):
                pass  # NO OP

            def initialize(self):
                pass  # NO OP

            def dispatch(self, job):
                self.called = True
                self.loop.stop()

        loop = get_ioloop()
        controller = MockedController('endpoint', 'multicast_endpoint',
                                      mock.sentinel.context, loop, arbiter,
                                      check_delay=-1.0)

        controller.dispatch((None, 'something'))
        controller.start()
        loop.start()
        self.assertTrue(controller.called)

    def _multicast_side_effect_helper(self, side_effect):
        arbiter = mock.MagicMock()
        loop = mock.MagicMock()
        context = mock.sentinel.context

        controller = circus.controller.Controller(
            'endpoint', DEFAULT_ENDPOINT_MULTICAST, context, loop, arbiter
        )

        with mock.patch('circus.util.create_udp_socket') as m:
            m.side_effect = side_effect
            circus.controller.create_udp_socket = m

            with mock.patch.object(logger, 'warning') as mock_logger_warn:
                controller._init_multicast_endpoint()
                self.assertTrue(mock_logger_warn.called)

    def test_multicast_ioerror(self):
        self._multicast_side_effect_helper(IOError)

    def test_multicast_oserror(self):
        self._multicast_side_effect_helper(OSError)

    def test_multicast_valueerror(self):
        arbiter = mock.MagicMock()
        loop = mock.MagicMock()
        context = mock.sentinel.context

        wrong_multicast_endpoint = 'udp://127.0.0.1:12027'
        controller = Controller('endpoint', wrong_multicast_endpoint,
                                context, loop, arbiter)

        with mock.patch.object(logger, 'warning') as mock_logger_warn:
            controller._init_multicast_endpoint()
            self.assertTrue(mock_logger_warn.called)

    def test_garbage_message(self):
        class MockedController(Controller):
            called = False

            def dispatch(self, job, future=None):
                self.called = True

            def send_response(self, mid, cid, msg, resp, cast=False):
                self.called = True

        arbiter = mock.MagicMock()
        loop = mock.MagicMock()
        context = mock.sentinel.context
        controller = MockedController('endpoint', 'multicast_endpoint',
                                      context, loop, arbiter)
        controller.handle_message(b'hello')
        self.assertFalse(controller.called)
        controller.handle_message([b'383ec229eb5d47f7bdd470dd3d6734a3',
                                   b'{"command":"add", "foo": "bar"}'])
        self.assertTrue(controller.called)


test_suite = EasyTestSuite(__name__)
