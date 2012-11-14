import unittest
import os
from circus.config import get_config
from circus.watcher import Watcher
from circus.process import Process
from circus.sockets import CircusSocket

HERE = os.path.join(os.path.dirname(__file__))

_CONF = {
    'issue137': os.path.join(HERE, 'issue137.ini'),
    'include': os.path.join(HERE, 'include.ini'),
    'issue210': os.path.join(HERE, 'issue210.ini'),
    'issue310': os.path.join(HERE, 'issue310.ini'),
    'hooks': os.path.join(HERE, 'hooks.ini'),
    'env_var': os.path.join(HERE, 'env_var.ini'),
    'env_section': os.path.join(HERE, 'env_section.ini'),
}


def hook(watcher, hook_name):
    pass


class TestConfig(unittest.TestCase):

    def test_issue310(self):
        '''
        https://github.com/mozilla-services/circus/pull/310

        Allow $(circus.sockets.name) to be used in args.
        '''
        conf = get_config(_CONF['issue310'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        socket = CircusSocket.load_from_config(conf['sockets'][0])
        watcher.initialize(None, {'web': socket}, None)
        process = Process(watcher._process_counter, watcher.cmd,
                          args=watcher.args, working_dir=watcher.working_dir,
                          shell=watcher.shell, uid=watcher.uid,
                          gid=watcher.gid, env=watcher.env,
                          rlimits=watcher.rlimits, spawn=False,
                          executable=watcher.executable,
                          use_fds=watcher.use_sockets, watcher=watcher)

        fd = watcher._get_sockets_fds()['web']
        formatted_args = process.format_args()

        self.assertEquals(formatted_args,
                          ['foo', '--fd', str(fd)])

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
        watchers_conf = {}
        for watcher_conf in conf['watchers']:
            watchers_conf[watcher_conf['name']] = watcher_conf
        watcher1 = Watcher.load_from_config(watchers_conf['watcher1'])
        watcher2 = Watcher.load_from_config(watchers_conf['watcher2'])

        self.assertEquals('lie', watcher1.env['CAKE'])
        self.assertEquals('cake', watcher2.env['LIE'])

        for watcher in [watcher1, watcher2]:
            self.assertEquals("%s:/bin" % os.getenv('PATH'),
                              watcher.env['PATH'])
