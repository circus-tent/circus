import unittest
import os
from circus.arbiter import ThreadedArbiter, ReloadArbiterException


HERE = os.path.join(os.path.dirname(__file__))

_CONF = {
    'reload_base': os.path.join(HERE, 'reload_base.ini'),
    'reload_numprocesses': os.path.join(HERE, 'reload_numprocesses.ini'),
    'reload_addwatchers': os.path.join(HERE, 'reload_addwatchers.ini'),
    'reload_delwatchers': os.path.join(HERE, 'reload_delwatchers.ini'),
    'reload_changewatchers': os.path.join(HERE, 'reload_changewatchers.ini'),
    'reload_addplugins': os.path.join(HERE, 'reload_addplugins.ini'),
    'reload_delplugins': os.path.join(HERE, 'reload_delplugins.ini'),
    'reload_changeplugins': os.path.join(HERE, 'reload_changeplugins.ini'),
    'reload_addsockets': os.path.join(HERE, 'reload_addsockets.ini'),
    'reload_delsockets': os.path.join(HERE, 'reload_delsockets.ini'),
    'reload_changesockets': os.path.join(HERE, 'reload_changesockets.ini'),
    'reload_changearbiter': os.path.join(HERE, 'reload_changearbiter.ini'),
}


class TestConfig(unittest.TestCase):

    def setUp(self):
        conf = _CONF['reload_base']
        self.a = ThreadedArbiter.load_from_config(conf)
        self.a.start()

        # initialize watchers
        for watcher in self.a.iter_watchers():
            self.a._watchers_names[watcher.name.lower()] = watcher

    def tearDown(self):
        self.a.stop()
        self.a.sockets.close_all()
        self.a.context.destroy()

    def test_watcher_names(self):
        watcher_names = [i.name for i in self.a.watchers]
        watcher_names.sort()
        self.assertEqual(watcher_names, ['plugin:myplugin', 'test1', 'test2'])

    def test_reload_numprocesses(self):
        w = self.a.get_watcher('test1')
        self.assertEqual(w.numprocesses, 1)
        self.a.reload_from_config(_CONF['reload_numprocesses'])
        self.assertEqual(w.numprocesses, 2)

    def test_reload_addwatchers(self):
        self.assertEqual(len(self.a.watchers), 3)

        self.a.reload_from_config(_CONF['reload_addwatchers'])
        self.assertEqual(len(self.a.watchers), 4)

    def test_reload_delwatchers(self):
        self.assertEqual(len(self.a.watchers), 3)

        self.a.reload_from_config(_CONF['reload_delwatchers'])
        self.assertEqual(len(self.a.watchers), 2)

    def test_reload_changewatchers(self):
        self.assertEqual(len(self.a.watchers), 3)
        w0 = self.a.get_watcher('test1')
        w1 = self.a.get_watcher('test2')

        self.a.reload_from_config(_CONF['reload_changewatchers'])
        self.assertEqual(len(self.a.watchers), 3)
        self.assertEqual(self.a.get_watcher('test1'), w0)
        self.assertNotEqual(self.a.get_watcher('test2'), w1)

    def test_reload_addplugins(self):
        self.assertEqual(len(self.a.watchers), 3)

        self.a.reload_from_config(_CONF['reload_addplugins'])
        self.assertEqual(len(self.a.watchers), 4)

    def test_reload_delplugins(self):
        self.assertEqual(len(self.a.watchers), 3)

        self.a.reload_from_config(_CONF['reload_delplugins'])
        self.assertEqual(len(self.a.watchers), 2)

    def test_reload_changeplugins(self):
        self.assertEqual(len(self.a.watchers), 3)
        p = self.a.get_watcher('plugin:myplugin')

        self.a.reload_from_config(_CONF['reload_changeplugins'])
        self.assertEqual(len(self.a.watchers), 3)
        self.assertNotEqual(self.a.get_watcher('plugin:myplugin'), p)

    def test_reload_addsockets(self):
        self.assertEqual(len(self.a.sockets), 1)

        self.a.reload_from_config(_CONF['reload_addsockets'])
        self.assertEqual(len(self.a.sockets), 2)

    def test_reload_delsockets(self):
        self.assertEqual(len(self.a.sockets), 1)

        self.a.reload_from_config(_CONF['reload_delsockets'])
        self.assertEqual(len(self.a.sockets), 0)

    def test_reload_changesockets(self):
        self.assertEqual(len(self.a.sockets), 1)
        s = self.a.get_socket('mysocket')

        self.a.reload_from_config(_CONF['reload_changesockets'])
        self.assertEqual(len(self.a.sockets), 1)
        self.assertNotEqual(self.a.get_socket('mysocket'), s)

    def test_reload_changearbiter(self):
        self.assertRaises(ReloadArbiterException,
                          self.a.reload_from_config,
                          _CONF['reload_changearbiter'])
