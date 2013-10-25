from circus.tests.support import TestCase, EasyTestSuite
from circus.controller import Controller

from zmq.eventloop import ioloop

import mock


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

        loop = ioloop.IOLoop()

        controller = MockedController('endpoint', 'multicast_endpoint',
                                      mock.sentinel.context, loop, arbiter, 
                                      check_delay=-1.0)

        controller.dispatch((None, 'something'))
        loop.add_timeout(loop.time() + 1, loop.stop)
        controller.start()
        loop.start()
        self.assertTrue(controller.called)

test_suite = EasyTestSuite(__name__)
