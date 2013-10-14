import unittest
import os
from mock import patch

from circus import logger
from circus.config import get_config
from circus.watcher import Watcher
from circus.process import Process
from circus.sockets import CircusSocket
from circus.util import replace_gnu_args


HERE = os.path.join(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(HERE, 'config')

_CONF = {
    'issue137': os.path.join(CONFIG_DIR, 'issue137.ini'),
    'include': os.path.join(CONFIG_DIR, 'include.ini'),
    'issue210': os.path.join(CONFIG_DIR, 'issue210.ini'),
    'issue310': os.path.join(CONFIG_DIR, 'issue310.ini'),
    'issue395': os.path.join(CONFIG_DIR, 'issue395.ini'),
    'hooks': os.path.join(CONFIG_DIR, 'hooks.ini'),
    'env_var': os.path.join(CONFIG_DIR, 'env_var.ini'),
    'env_section': os.path.join(CONFIG_DIR, 'env_section.ini'),
    'multiple_wildcard': os.path.join(CONFIG_DIR, 'multiple_wildcard.ini'),
    'empty_include': os.path.join(CONFIG_DIR, 'empty_include.ini'),
    'circus': os.path.join(CONFIG_DIR, 'circus.ini'),
    'nope': os.path.join(CONFIG_DIR, 'nope.ini'),
    'unexistant': os.path.join(CONFIG_DIR, 'unexistant.ini'),
    'issue442': os.path.join(CONFIG_DIR, 'issue442.ini'),
    'expand_vars': os.path.join(CONFIG_DIR, 'expand_vars.ini'),
    'issue546': os.path.join(CONFIG_DIR, 'issue546.ini'),
    'env_everywhere': os.path.join(CONFIG_DIR, 'env_everywhere.ini'),
    'copy_env': os.path.join(CONFIG_DIR, 'copy_env.ini'),
    'issue567': os.path.join(CONFIG_DIR, 'issue567.ini')
}


def hook(watcher, hook_name):
    "Yeah that's me"
    pass


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.saved = os.environ.copy()

    def tearDown(self):
        os.environ = self.saved

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

    def test_expand_vars(self):
        '''
        https://github.com/mozilla-services/circus/pull/554
        '''
        conf = get_config(_CONF['expand_vars'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['stdout_stream']['filename'], '/tmp/echo.log')

    def test_dashes(self):
        conf = get_config(_CONF['issue546'])
        replaced = replace_gnu_args(conf['watchers'][0]['cmd'],
                                    sockets={'some-socket': 3})
        self.assertEqual(replaced, '../bin/chaussette --fd 3')

    def test_env_everywhere(self):
        conf = get_config(_CONF['env_everywhere'])

        self.assertEqual(conf['endpoint'], 'tcp://127.0.0.1:1234')
        self.assertEqual(conf['sockets'][0]['path'], '/var/run/broken.sock')
        self.assertEqual(conf['plugins'][0]['use'], 'bad.has.been.broken')

    def test_copy_env(self):
        # #564 make sure we respect copy_env
        os.environ['BAM'] = '1'
        conf = get_config(_CONF['copy_env'])
        for watcher in conf['watchers']:
            if watcher['name'] == 'watcher1':

                self.assertFalse('BAM' in watcher['env'])
            else:
                self.assertTrue('BAM' in watcher['env'])
            self.assertTrue('TEST1' in watcher['env'])

    def test_issue567(self):
        os.environ['GRAVITY'] = 'down'
        conf = get_config(_CONF['issue567'])

        # make sure the global environment makes it into the cfg environment
        # even without [env] section
        self.assertEqual(conf['watchers'][0]['cmd'], 'down')
