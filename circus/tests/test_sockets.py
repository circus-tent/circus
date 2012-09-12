import os
from circus.tests.support import unittest
from circus.sockets import CircusSocket, CircusSockets


TRAVIS = os.getenv('TRAVIS', False)


class TestSockets(unittest.TestCase):

    def test_socket(self):
        if TRAVIS:
            return
        sock = CircusSocket('somename', 'localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

    def test_manager(self):
        if TRAVIS:
            return

        mgr = CircusSockets()

        for i in range(5):
            mgr.add(str(i), 'localhost', 0)

        port = mgr['1'].port
        try:
            mgr.bind_and_listen_all()
            # we should have a port now
            self.assertNotEqual(port, mgr['1'].port)
        finally:
            mgr.close_all()

    def test_load_from_config(self):
        """Test the load_from_config function"""
        config = {'name': 'test_socket',
                  'host': '0.0.0.0',
                  'port': '5000'}                  
        sock = CircusSocket.load_from_config(config)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()
