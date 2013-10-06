import sys
import os

import tempfile
from copy import copy

from circus.circusd import get_maxfd, daemonize, main
from circus import circusd
from circus.arbiter import Arbiter
from circus.util import REDIRECT_TO
from circus import util
from circus.tests.support import has_gevent, TestCase, skipIf, EasyTestSuite


CIRCUS_INI = os.path.join(os.path.dirname(__file__), 'config', 'circus.ini')


class TestCircusd(TestCase):

    def setUp(self):
        self.saved = dict(sys.modules)
        self.argv = copy(sys.argv)
        self.starter = Arbiter.start
        Arbiter.start = lambda x: None
        self.exit = sys.exit
        sys.exit = lambda x: None
        self._files = []
        self.fork = os.fork
        os.fork = self._forking
        self.setsid = os.setsid
        os.setsid = lambda: None
        self.forked = 0
        self.closerange = circusd.closerange
        circusd.closerange = lambda x, y: None
        self.open = os.open
        os.open = self._open
        self.dup2 = os.dup2
        os.dup2 = lambda x, y: None
        self.stop = Arbiter.stop
        Arbiter.stop = lambda x: None
        self.config = util.configure_logger
        circusd.configure_logger = util.configure_logger = self._logger

    def _logger(self, *args, **kw):
        pass

    def _open(self, path, *args, **kw):
        if path == REDIRECT_TO:
            return
        return self.open(path, *args, **kw)

    def tearDown(self):
        circusd.configure_logger = util.configure_logger = self.config
        Arbiter.stop = self.stop
        sys.argv = self.argv
        os.dup2 = self.dup2
        os.open = self.open
        circusd.closerange = self.closerange
        os.setsid = self.setsid
        sys.modules = self.saved
        Arbiter.start = self.starter
        sys.exit = self.exit
        os.fork = self.fork
        for file in self._files:
            if os.path.exists(file):
                os.remove(file)
        self.forked = 0

    def _forking(self):
        self.forked += 1
        return 0

    @skipIf(not has_gevent(), "Only when Gevent is loaded")
    def test_daemon(self):
        # if gevent is loaded, we want to prevent
        # daemonize() to work
        self.assertRaises(ValueError, daemonize)

        for module in sys.modules.keys():
            if module.startswith('gevent'):
                del sys.modules[module]

        from gevent.dns import resolve_ipv4     # NOQA
        self.assertRaises(ValueError, daemonize)

    def test_maxfd(self):
        max = get_maxfd()
        self.assertTrue(isinstance(max, int))

    @skipIf(has_gevent(), "Gevent is loaded")
    def test_daemonize(self):
        def check_pid(pid):
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            else:
                return True

        daemonize()
        self.assertEqual(self.forked, 2)

    def _get_file(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        self._files.append(path)
        return path

    def test_main(self):

        def _check_pid(cls):
            self.assertTrue(os.path.exists(pid_file))

        Arbiter.start = _check_pid
        pid_file = self._get_file()
        sys.argv = ['circusd', CIRCUS_INI, '--pidfile', pid_file]
        main()
        self.assertFalse(os.path.exists(pid_file))

test_suite = EasyTestSuite(__name__)
