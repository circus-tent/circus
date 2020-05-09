import os
import socket
import tempfile
try:
    import IN
except ImportError:
    pass
from unittest import mock
import fcntl

from circus.tests.support import TestCase, skipIf, EasyTestSuite, IS_WINDOWS
from circus.sockets import CircusSocket, CircusSockets


def so_bindtodevice_supported():
    try:
        if hasattr(IN, 'SO_BINDTODEVICE'):
            return True
    except NameError:
        pass
    return False


def is_nonblock(fd):
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    nonblock = fl & os.O_NONBLOCK
    return nonblock != 0


class TestSockets(TestCase):

    def setUp(self):
        super(TestSockets, self).setUp()
        self.files = []

    def tearDown(self):
        for file_ in self.files:
            if os.path.exists(file_):
                os.remove(file_)

        super(TestSockets, self).tearDown()

    def _get_file(self):
        fd, _file = tempfile.mkstemp()
        os.close(fd)
        self.files.append(_file)
        return _file

    def _get_tmp_filename(self):
        # XXX horrible way to get a filename
        fd, _file = tempfile.mkstemp()
        os.close(fd)
        os.remove(_file)
        return _file

    def test_socket(self):
        sock = CircusSocket('somename', 'localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

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
        sock.close()

    def test_load_from_config_unknown_proto(self):
        """Unknown proto in the config raises an error."""
        config = {'name': '', 'proto': 'foo'}
        self.assertRaises(socket.error, CircusSocket.load_from_config, config)

    @skipIf(IS_WINDOWS, "Unix sockets not supported on this platform")
    def test_load_from_config_umask(self):
        sockfile = self._get_tmp_filename()
        config = {'name': 'somename', 'path': sockfile, 'umask': 0}
        sock = CircusSocket.load_from_config(config)
        try:
            self.assertEqual(sock.umask, 0)
        finally:
            sock.close()

    @skipIf(IS_WINDOWS, "Unix sockets not supported on this platform")
    def test_load_from_config_replace(self):
        sockfile = self._get_file()

        config = {'name': 'somename', 'path': sockfile, 'replace': False}
        sock = CircusSocket.load_from_config(config)
        try:
            self.assertRaises(OSError, sock.bind_and_listen)
        finally:
            sock.close()

        config = {'name': 'somename', 'path': sockfile, 'replace': True}
        sock = CircusSocket.load_from_config(config)
        sock.bind_and_listen()
        try:
            self.assertEqual(sock.replace, True)
        finally:
            sock.close()

    @skipIf(IS_WINDOWS, "Unix sockets not supported on this platform")
    def test_load_from_config_blocking(self):
        # test default to false
        config = {'name': 'somename', 'host': 'localhost', 'port': 0}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.blocking, False)
        sock.bind_and_listen()
        self.assertTrue(is_nonblock(sock.fileno()))
        sock.close()

        # test when true
        config = {'name': 'somename', 'host': 'localhost', 'port': 0,
                  'blocking': True}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.blocking, True)
        sock.bind_and_listen()
        self.assertFalse(is_nonblock(sock.fileno()))
        sock.close()

    @skipIf(IS_WINDOWS, "Unix sockets not supported on this platform")
    def test_unix_socket(self):
        sockfile = self._get_tmp_filename()
        sock = CircusSocket('somename', path=sockfile, umask=0)
        try:
            sock.bind_and_listen()
            self.assertTrue(os.path.exists(sockfile))
            permissions = oct(os.stat(sockfile).st_mode)[-3:]
            self.assertEqual(permissions, '777')
        finally:
            sock.close()

    @skipIf(IS_WINDOWS, "Unix sockets not supported on this platform")
    def test_unix_cleanup(self):
        sockets = CircusSockets()
        sockfile = self._get_tmp_filename()
        try:
            sockets.add('unix', path=sockfile)
            sockets.bind_and_listen_all()
            self.assertTrue(os.path.exists(sockfile))
        finally:
            sockets.close_all()
            self.assertTrue(not os.path.exists(sockfile))

    @skipIf(not so_bindtodevice_supported(),
            'SO_BINDTODEVICE unsupported')
    def test_bind_to_interface(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'interface': 'lo'}

        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.interface, config['interface'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            sock.setsockopt.assert_any_call(socket.SOL_SOCKET,
                                            IN.SO_BINDTODEVICE,
                                            config['interface'] + '\0')
        finally:
            sock.close()

    def test_inet6(self):
        config = {'name': '', 'host': '::1', 'port': 0,
                  'family': 'AF_INET6'}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.host, config['host'])
        self.assertEqual(sock.port, config['port'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            # we should have got a port set
            self.assertNotEqual(sock.port, 0)
        finally:
            sock.close()

    @skipIf(not hasattr(socket, 'SO_REUSEPORT'),
            'socket.SO_REUSEPORT unsupported')
    def test_reuseport_supported(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'so_reuseport': True}

        sock = CircusSocket.load_from_config(config)
        try:
            sockopt = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT)
        except socket.error:
            # see #699
            return
        finally:
            sock.close()

        self.assertEqual(sock.so_reuseport, True)
        self.assertNotEqual(sockopt, 0)

    def test_reuseport_unsupported(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'so_reuseport': True}
        saved = None

        try:
            if hasattr(socket, 'SO_REUSEPORT'):
                saved = socket.SO_REUSEPORT
                del socket.SO_REUSEPORT
            sock = CircusSocket.load_from_config(config)
            self.assertEqual(sock.so_reuseport, False)
        finally:
            if saved is not None:
                socket.SO_REUSEPORT = saved
            sock.close()

    @skipIf(not hasattr(os, 'set_inheritable'),
            'os.set_inheritable unsupported')
    @skipIf(IS_WINDOWS, "Unix sockets not supported on this platform")
    def test_set_inheritable(self):
        sockfile = self._get_tmp_filename()
        sock = CircusSocket('somename', path=sockfile, umask=0)
        try:
            sock.bind_and_listen()
            self.assertTrue(sock.get_inheritable())
        finally:
            sock.close()


test_suite = EasyTestSuite(__name__)
