import unittest
import os
from circus.config import get_config
from circus.watcher import Watcher

HERE = os.path.join(os.path.dirname(__file__))

_CONF = {
    'issue137': os.path.join(HERE, 'issue137.ini'),
    'include': os.path.join(HERE, 'include.ini'),
    'issue210': os.path.join(HERE, 'issue210.ini'),
}


class TestConfig(unittest.TestCase):

    def test_issue137(self):
        conf = get_config(_CONF['issue137'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['uid'], 'me')

    def test_include_wildcards(self):
        conf = get_config(_CONF['include'])
        watchers = conf['watchers']
        self.assertEquals(len(watchers), 4)

    def test_watcher_graceful_timeout(self):
        conf = get_config(_CONF['issue210'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()
