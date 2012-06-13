import unittest
from circus.sockets import CircusSocket, CircusSocketManager


class TestSockets(unittest.TestCase):

    def test_socket(self):
        sock = CircusSocket('localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

    def test_manager(self):
        mgr = CircusSocketManager()

        for i in range(5):
            mgr.add('localhost', 0)

        self.assertEqual(len(mgr.names), 5)

        one = mgr.names[0]
        mgr.get_fileno(*one)
        try:
            mgr.bind_and_listen_all()
            two = mgr.names[0]
            # we should have a port now
            self.assertNotEqual(one, two)
        finally:
            mgr.close_all()
