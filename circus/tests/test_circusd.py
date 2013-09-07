import unittest
import sys
import os
import tempfile

from circus.circusd import get_maxfd, daemonize, main
from circus.arbiter import Arbiter


CIRCUS_INI = os.path.join(os.path.dirname(__file__), 'circus.ini')


class TestCircusd(unittest.TestCase):

    def setUp(self):
        self.saved = dict(sys.modules)
        self.starter = Arbiter.start
        Arbiter.start = lambda x: None
        self.exit = sys.exit
        sys.exit = lambda x: None
        self._files = []

    def tearDown(self):
        sys.modules = self.saved
        Arbiter.start = self.starter
        sys.exit = self.exit
        for file in self._files:
            if os.path.exists(file):
                os.remove(file)

    def test_daemon(self):
        # if gevent is loaded, we want to prevent
        # daemonize() to work
        try:
            import gevent       # NOQA
        except ImportError:
            return

        self.assertRaises(ValueError, daemonize)

        for module in sys.modules.keys():
            if module.startswith('gevent'):
                del sys.modules[module]

        from gevent.dns import resolve_ipv4     # NOQA
        self.assertRaises(ValueError, daemonize)

    def test_maxfd(self):
        max = get_maxfd()
        self.assertTrue(isinstance(max, int))

    def test_daemonize(self):
        def check_pid(pid):
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            else:
                return True

        child_pid = daemonize(parent_exit=False)
        self.assertTrue(check_pid(child_pid))
        os.kill(child_pid, 9)

    def _get_file(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        self._files.append(path)
        return path

    def test_main(self):

        def _check_pid(cls):
            self.assertTrue(os.path.exists(pid_file))

        Arbiter.start = _check_pid

        saved = list(sys.argv)
        pid_file = self._get_file()

        sys.argv = ['circusd', CIRCUS_INI, '--pidfile', pid_file]
        try:
            main()
        finally:
            sys.argv[:] = saved

        self.assertFalse(os.path.exists(pid_file))
