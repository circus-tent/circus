import unittest
import sys

from circus.circusd import daemonize


class TestCircusd(unittest.TestCase):

    def setUp(self):
        self.saved = dict(sys.modules)

    def tearDown(self):
        sys.modules = self.saved

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
