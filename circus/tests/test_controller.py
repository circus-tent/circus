from unittest import TestCase
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

        loop = ioloop.IOLoop.instance()

        controller = MockedController('endpoint', 'multicast_endpoint',
                                      mock.sentinel.context, loop, arbiter)

        controller.add_job(None, 'something')
        loop.add_timeout(loop.time() + 1, loop.stop)
        controller.start()
        loop.start()
        self.assertTrue(controller.called)
