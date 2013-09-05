import unittest
import os
from mock import patch

from circus import logger
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
    'issue395': os.path.join(HERE, 'issue395.ini'),
    'hooks': os.path.join(HERE, 'hooks.ini'),
    'env_var': os.path.join(HERE, 'env_var.ini'),
    'env_section': os.path.join(HERE, 'env_section.ini'),
    'multiple_wildcard': os.path.join(HERE, 'multiple_wildcard.ini'),
    'empty_include': os.path.join(HERE, 'empty_include.ini'),
    'circus': os.path.join(HERE, 'circus.ini'),
    'nope': os.path.join(HERE, 'nope.ini'),
    'unexistant': os.path.join(HERE, 'unexistant.ini'),
    'issue442': os.path.join(HERE, 'issue442.ini')
}


def hook(watcher, hook_name):
    "Yeah that's me"
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
        process = Process(watcher._nextwid, watcher.cmd,
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

    def test_include_multiple_wildcards(self):
        conf = get_config(_CONF['multiple_wildcard'])
        watchers = conf['watchers']
        self.assertEquals(len(watchers), 3)

    @patch.object(logger, 'warn')
    def test_empty_include(self, mock_logger_warn):
        """https://github.com/mozilla-services/circus/pull/473"""
        try:
            get_config(_CONF['empty_include'])
        except:
            self.fail('Non-existent includes should not raise')
        self.assertTrue(mock_logger_warn.called)

    def test_watcher_graceful_timeout(self):
        conf = get_config(_CONF['issue210'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()

    def test_hooks(self):
        conf = get_config(_CONF['hooks'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEqual(watcher.hooks['before_start'].__doc__, hook.__doc__)
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

        self.assertEquals('test1', watcher1.env['TEST1'])
        self.assertEquals('test1', watcher2.env['TEST1'])

        self.assertEquals('test2', watcher1.env['TEST2'])
        self.assertEquals('test2', watcher2.env['TEST2'])

        self.assertEquals('test3', watcher1.env['TEST3'])
        self.assertEquals('test3', watcher2.env['TEST3'])

    def test_issue395(self):
        conf = get_config(_CONF['issue395'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['graceful_timeout'], 88)

    def test_pidfile(self):
        conf = get_config(_CONF['circus'])
        self.assertEquals(conf['pidfile'], 'pidfile')

    def test_logoutput(self):
        conf = get_config(_CONF['circus'])
        self.assertEquals(conf['logoutput'], 'logoutput')

    def test_loglevel(self):
        conf = get_config(_CONF['circus'])
        self.assertEquals(conf['loglevel'], 'debug')

    def test_override(self):
        conf = get_config(_CONF['multiple_wildcard'])
        watchers = conf['watchers']
        self.assertEquals(len(watchers), 3)
        watchers = conf['watchers']
        watchers.sort()
        self.assertEquals(watchers[2]['env']['INI'], 'private.ini')
        self.assertEqual(conf['check'], 555)

    def test_config_unexistant(self):
        self.assertRaises(IOError, get_config, _CONF['unexistant'])

    def test_variables_everywhere(self):
        os.environ['circus_stats_endpoint'] = 'tcp://0.0.0.0:9876'
        os.environ['circus_statsd'] = 'True'

        # these will be overriden
        os.environ['circus_uid'] = 'ubuntu'
        os.environ['circus_gid'] = 'ubuntu'

        conf = get_config(_CONF['issue442'])

        self.assertEqual(conf['stats_endpoint'], 'tcp://0.0.0.0:9876')
        self.assertTrue(conf['statsd'])
        self.assertEqual(conf['watchers'][0]['uid'], 'tarek')
        self.assertEqual(conf['watchers'][0]['gid'], 'root')
