import os
import socket
import tempfile
import IN

import mock

from circus.tests.support import unittest
from circus.sockets import CircusSocket, CircusSockets


TRAVIS = os.getenv('TRAVIS', False)


class TestSockets(unittest.TestCase):

    @unittest.skipIf(TRAVIS, "Running in Travis")
    def test_socket(self):
        sock = CircusSocket('somename', 'localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

    @unittest.skipIf(TRAVIS, "Running in Travis")
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

    def test_load_from_config_no_proto(self):
        """When no proto in the config, the default (0) is used."""
        config = {'name': ''}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.proto, 0)

    def test_load_from_config_unknown_proto(self):
        """Unknown proto in the config raises an error."""
        config = {'name': '', 'proto': 'foo'}
        self.assertRaises(socket.error, CircusSocket.load_from_config, config)

    @unittest.skipIf(TRAVIS, "Running in Travis")
    def test_load_from_config_umask(self):
        fd, sockfile = tempfile.mkstemp()
        os.close(fd)
        os.remove(sockfile)

        config = {'name': 'somename', 'path': sockfile, 'umask': 0}
        sock = CircusSocket.load_from_config(config)
        try:
            self.assertEqual(sock.umask, 0)
        finally:
            sock.close()

    @unittest.skipIf(TRAVIS, "Running in Travis")
    def test_unix_socket(self):
        fd, sockfile = tempfile.mkstemp()
        os.close(fd)
        os.remove(sockfile)

        sock = CircusSocket('somename', path=sockfile, umask=0)
        try:
            sock.bind_and_listen()
            self.assertTrue(os.path.exists(sockfile))
            permissions = oct(os.stat(sockfile).st_mode)[-3:]
            self.assertEqual(permissions, '777')
        finally:
            sock.close()

    @unittest.skipIf(TRAVIS, "Running in Travis")
    def test_unix_cleanup(self):
        sockets = CircusSockets()
        fd, sockfile = tempfile.mkstemp()
        os.close(fd)
        os.remove(sockfile)

        try:
            sockets.add('unix', path=sockfile)
            sockets.bind_and_listen_all()
            self.assertTrue(os.path.exists(sockfile))
        finally:
            sockets.close_all()
            self.assertTrue(not os.path.exists(sockfile))

    @unittest.skipIf(TRAVIS, "Running in Travis")
    def test_bind_to_interface(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'interface': 'lo'}

        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.interface, config['interface'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            sock.setsockopt.assert_any_call(socket.SOL_SOCKET, 
                IN.SO_BINDTODEVICE, config['interface'] + '\0')
        finally:
            sock.close()
