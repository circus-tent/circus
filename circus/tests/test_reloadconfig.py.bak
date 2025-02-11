import os
import tornado
import tornado.testing

from circus.arbiter import Arbiter
from circus.tests.support import EasyTestSuite


HERE = os.path.join(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(HERE, 'config')

_CONF = {
    'reload_base': os.path.join(CONFIG_DIR, 'reload_base.ini'),
    'reload_numprocesses': os.path.join(CONFIG_DIR, 'reload_numprocesses.ini'),
    'reload_addwatchers': os.path.join(CONFIG_DIR, 'reload_addwatchers.ini'),
    'reload_delwatchers': os.path.join(CONFIG_DIR, 'reload_delwatchers.ini'),
    'reload_changewatchers': os.path.join(CONFIG_DIR,
                                          'reload_changewatchers.ini'),
    'reload_addplugins': os.path.join(CONFIG_DIR, 'reload_addplugins.ini'),
    'reload_delplugins': os.path.join(CONFIG_DIR, 'reload_delplugins.ini'),
    'reload_changeplugins': os.path.join(CONFIG_DIR,
                                         'reload_changeplugins.ini'),
    'reload_addsockets': os.path.join(CONFIG_DIR, 'reload_addsockets.ini'),
    'reload_delsockets': os.path.join(CONFIG_DIR, 'reload_delsockets.ini'),
    'reload_changesockets': os.path.join(CONFIG_DIR,
                                         'reload_changesockets.ini'),
    'reload_changearbiter': os.path.join(CONFIG_DIR,
                                         'reload_changearbiter.ini'),
    'reload_statsd': os.path.join(CONFIG_DIR, 'reload_statsd.ini'),
}


class FakeSocket(object):
    closed = False

    def send_multipart(self, *args):
        pass
    close = send_multipart


class TestConfig(tornado.testing.AsyncTestCase):

    def setUp(self):
        super(TestConfig, self).setUp()
        self.a = self._load_base_arbiter()

    @tornado.gen.coroutine
    def _tearDown(self):
        yield self._tear_down_arbiter(self.a)

    @tornado.gen.coroutine
    def _tear_down_arbiter(self, a):
        for watcher in a.iter_watchers():
            yield watcher._stop()
        a.sockets.close_all()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.current()

    def _load_base_arbiter(self, name='reload_base'):
        loop = tornado.ioloop.IOLoop.current()
        a = Arbiter.load_from_config(_CONF[name], loop=loop)
        a.evpub_socket = FakeSocket()
        # initialize watchers
        for watcher in a.iter_watchers():
            a._watchers_names[watcher.name.lower()] = watcher
        return a

    def test_watcher_names(self):
        watcher_names = sorted(i.name for i in self.a.watchers)
        self.assertEqual(watcher_names, ['plugin:myplugin', 'test1', 'test2'])

    @tornado.testing.gen_test
    def test_reload_numprocesses(self):
        w = self.a.get_watcher('test1')
        self.assertEqual(w.numprocesses, 1)
        yield self.a.reload_from_config(_CONF['reload_numprocesses'])
        self.assertEqual(w.numprocesses, 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_addwatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_addwatchers'])
        self.assertEqual(len(self.a.watchers), 4)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_delwatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_delwatchers'])
        self.assertEqual(len(self.a.watchers), 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_changewatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        w0 = self.a.get_watcher('test1')
        w1 = self.a.get_watcher('test2')
        yield self.a.reload_from_config(_CONF['reload_changewatchers'])
        self.assertEqual(len(self.a.watchers), 3)
        self.assertEqual(self.a.get_watcher('test1'), w0)
        self.assertNotEqual(self.a.get_watcher('test2'), w1)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_addplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_addplugins'])
        self.assertEqual(len(self.a.watchers), 4)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_delplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        yield self.a.reload_from_config(_CONF['reload_delplugins'])
        self.assertEqual(len(self.a.watchers), 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_changeplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        p = self.a.get_watcher('plugin:myplugin')
        yield self.a.reload_from_config(_CONF['reload_changeplugins'])
        self.assertEqual(len(self.a.watchers), 3)
        self.assertNotEqual(self.a.get_watcher('plugin:myplugin'), p)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_addsockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        yield self.a.reload_from_config(_CONF['reload_addsockets'])
        self.assertEqual(len(self.a.sockets), 2)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_delsockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        yield self.a.reload_from_config(_CONF['reload_delsockets'])
        self.assertEqual(len(self.a.sockets), 0)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_changesockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        s = self.a.get_socket('mysocket')
        yield self.a.reload_from_config(_CONF['reload_changesockets'])
        self.assertEqual(len(self.a.sockets), 1)
        self.assertNotEqual(self.a.get_socket('mysocket'), s)
        yield self._tearDown()

    @tornado.testing.gen_test
    def test_reload_envdictparsed(self):
        # environ var that needs a `circus.util.parse_env_dict` treatment
        os.environ['SHRUBBERY'] = ' NI '
        a = self._load_base_arbiter()
        try:
            w = a.get_watcher('test1')
            yield a.reload_from_config(_CONF['reload_base'])
            self.assertEqual(a.get_watcher('test1'), w)
        finally:
            del os.environ['SHRUBBERY']
            yield self._tear_down_arbiter(a)

    @tornado.testing.gen_test
    def test_reload_ignorearbiterwatchers(self):
        a = self._load_base_arbiter('reload_statsd')
        statsd = a.get_watcher('circusd-stats')
        yield a.reload_from_config(_CONF['reload_statsd'])
        self.assertEqual(statsd, a.get_watcher('circusd-stats'))


test_suite = EasyTestSuite(__name__)
