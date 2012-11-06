import unittest
import os
from circus.config import get_config
from circus.watcher import Watcher

HERE = os.path.join(os.path.dirname(__file__))

_CONF = {
    'issue137': os.path.join(HERE, 'issue137.ini'),
    'include': os.path.join(HERE, 'include.ini'),
    'issue210': os.path.join(HERE, 'issue210.ini'),
    'hooks': os.path.join(HERE, 'hooks.ini'),
    'env_var': os.path.join(HERE, 'env_var.ini'),
    'env_section': os.path.join(HERE, 'env_section.ini'),
}


def hook(watcher, hook_name):
    pass


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

    def test_hooks(self):
        conf = get_config(_CONF['hooks'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEqual(watcher.hooks['before_start'], hook)
        self.assertTrue('before_start' not in watcher.ignore_hook_failure)

    def test_watcher_env_var(self):
        conf = get_config(_CONF['env_var'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEquals("%s:/bin" % os.getenv('PATH'), watcher.env['PATH'])
        watcher.stop()
    
    def test_env_section(self):
        conf = get_config(_CONF['env_section'])
        watchers = []
        watchers.append(Watcher.load_from_config(conf['watchers'][0]))
        watchers.append(Watcher.load_from_config(conf['watchers'][1]))
        
        self.assertEquals('lie', watchers[0].env['CAKE'])
        self.assertEquals('cake', watchers[1].env['LIE'])
        
        for watcher in watchers:
            self.assertEquals("%s:/bin" % os.getenv('PATH'), watcher.env['PATH'])
            watcher.stop()
