import unittest


from circus.discovery import AutoDiscovery

from zmq.eventloop import ioloop


class TestDiscover(unittest.TestCase):

    def test_discovery_callback(self):
        payload = "Beer. Now there's a temporary solution."
        loop = ioloop.IOLoop.instance()

        self.callback_called = False

        def cb(data):
            received_data = data
            self.assertEquals(received_data, payload)
            loop.stop()
            self.callback_called = True

        AutoDiscovery('udp://237.219.251.97:12027', loop, payload, cb)
        loop.add_timeout(loop.time() + 1, loop.stop)

        loop.start()
        self.assertTrue(self.callback_called)
