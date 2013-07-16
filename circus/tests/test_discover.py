import unittest
import mock

from circus.discovery import AutoDiscovery
from circus.arbiter import Arbiter

from zmq.eventloop import ioloop


class TestDiscover(unittest.TestCase):

    def test_discovery_callback(self):
        payload = "Beer. Now there's a temporary solution."
        loop = ioloop.IOLoop.instance()

        self.received_data = None

        def cb(data, emitter_addr, send_message):
            self.received_data = data
            loop.stop()

        AutoDiscovery('udp://237.219.251.97:12027', loop, payload, cb)
        loop.add_timeout(loop.time() + 1, loop.stop)

        loop.start()
        self.assertEquals(self.received_data['nodes'], payload)


class TestArbiterDiscovery(unittest.TestCase):

    def setUp(self):
        class ArbiterMock(object):
            def __init__(self):
                self.nodes_directory = {'arbiter': set(['tcp://0.0.0.0:5555'])}
                self.fqdn = 'arbiter'

        self.arbiter = ArbiterMock()
        self.arbiter.__class__ = Arbiter
        self.send_message = mock.MagicMock()

    def test_add_new_node(self):
        known_nodes = {'local': set(['tcp://127.0.0.1']),
                       'distant': set(['tcp://0.0.0.0:5555']),
                       'fixedip': set(['tcp://1.2.3.4:5678'])}

        Arbiter.add_new_node(self.arbiter,
                             {'type': 'new-node', 'nodes': known_nodes},
                             ('192.168.1.1', 12345), self.send_message)
        self.assertEquals(len(self.send_message.call_args_list), 1)

        # Test that the values are replaced propertly:
        # - 0.0.0.0 => the address of the callee
        # - 127.0.0.1 => removed
        self.assertEquals(self.arbiter.nodes_directory,
                          {'distant': set(['tcp://192.168.1.1:5555']),
                           'arbiter': set(['tcp://0.0.0.0:5555']),
                           'fixedip': set(['tcp://1.2.3.4:5678']),
                           'local': set()})

    def test_add_new_node_ack(self):
        known_nodes = {'local': set(['tcp://127.0.0.1']),
                       'distant': set(['tcp://0.0.0.0:5555']),
                       'fixedip': set(['tcp://1.2.3.4:5678'])}

        Arbiter.add_new_node(self.arbiter,
                             {'type': 'new-node-ack', 'nodes': known_nodes},
                             ('192.168.1.1', 12345), self.send_message)
        self.assertEquals(len(self.send_message.call_args_list), 0)
