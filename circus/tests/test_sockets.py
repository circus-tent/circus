import os
from circus.tests.support import unittest
from circus.sockets import CircusSocket, CircusSockets

TRAVIS = os.getenv('TRAVIS', False)


class TestSockets(unittest.TestCase):

    @unittest.skipIf(TRAVIS, "Unable to bind a socket on travis")
    def test_socket(self):
        sock = CircusSocket('somename', 'localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

    @unittest.skipIf(TRAVIS, "Unable to bind a socket on travis")
    def test_manager(self):
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
