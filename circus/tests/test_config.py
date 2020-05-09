import os
import signal
from unittest.mock import patch

from circus import logger
from circus.arbiter import Arbiter
from circus.config import get_config
from circus.watcher import Watcher
from circus.process import Process
from circus.sockets import CircusSocket
from circus.tests.support import TestCase, EasyTestSuite, IS_WINDOWS
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
    'find_hook_in_pythonpath': os.path.join(CONFIG_DIR,
                                            'find_hook_in_pythonpath.ini'),
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
    'env_sensecase': os.path.join(CONFIG_DIR, 'env_sensecase.ini'),
    'issue567': os.path.join(CONFIG_DIR, 'issue567.ini'),
    'issue594': os.path.join(CONFIG_DIR, 'issue594.ini'),
    'reuseport': os.path.join(CONFIG_DIR, 'reuseport.ini'),
    'issue651': os.path.join(CONFIG_DIR, 'issue651.ini'),
    'issue665': os.path.join(CONFIG_DIR, 'issue665.ini'),
    'issue680': os.path.join(CONFIG_DIR, 'issue680.ini'),
    'virtualenv': os.path.join(CONFIG_DIR, 'virtualenv.ini'),
    'empty_section': os.path.join(CONFIG_DIR, 'empty_section.ini'),
    'issue1088': os.path.join(CONFIG_DIR, 'issue1088.ini')
}


def hook(watcher, hook_name):
    "Yeah that's me"
    pass


class TestConfig(TestCase):

    def setUp(self):
        self.saved = os.environ.copy()

    def tearDown(self):
        os.environ = self.saved

    def test_issue310(self):
        '''
        https://github.com/circus-tent/circus/pull/310

        Allow $(circus.sockets.name) to be used in args.
        '''
        conf = get_config(_CONF['issue310'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        socket = CircusSocket.load_from_config(conf['sockets'][0])
        try:
            watcher.initialize(None, {'web': socket}, None)

            if IS_WINDOWS:
                # We can't close the sockets on Windows as we
                # are redirecting stdout
                watcher.use_sockets = True

            process = Process('test', watcher._nextwid, watcher.cmd,
                              args=watcher.args,
                              working_dir=watcher.working_dir,
                              shell=watcher.shell, uid=watcher.uid,
                              gid=watcher.gid, env=watcher.env,
                              rlimits=watcher.rlimits, spawn=False,
                              executable=watcher.executable,
                              use_fds=watcher.use_sockets,
                              watcher=watcher)

            sockets_fds = watcher._get_sockets_fds()
            formatted_args = process.format_args(sockets_fds=sockets_fds)

            fd = sockets_fds['web']
            self.assertEqual(formatted_args,
                             ['foo', '--fd', str(fd)])
        finally:
            socket.close()

    def test_issue137(self):
        conf = get_config(_CONF['issue137'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['uid'], 'me')

    def test_issues665(self):
        '''
        https://github.com/circus-tent/circus/pull/665

        Ensure args formatting when shell = True.
        '''
        conf = get_config(_CONF['issue665'])

        def load(watcher_conf):
            watcher = Watcher.load_from_config(watcher_conf.copy())

            # Make sure we don't close the sockets as we will be
            # launching the Watcher with IS_WINDOWS=True
            watcher.use_sockets = True

            process = Process('test', watcher._nextwid, watcher.cmd,
                              args=watcher.args,
                              working_dir=watcher.working_dir,
                              shell=watcher.shell, uid=watcher.uid,
                              gid=watcher.gid, env=watcher.env,
                              rlimits=watcher.rlimits, spawn=False,
                              executable=watcher.executable,
                              use_fds=watcher.use_sockets,
                              watcher=watcher)
            return process.format_args()

        import circus.process

        try:
            # force nix
            circus.process.IS_WINDOWS = False

            # without shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][0])
                self.assertEqual(formatted_args, ['foo --fd'])
                self.assertFalse(mock_logger_warn.called)

            # with shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][1])
                self.assertEqual(formatted_args,
                                 ['foo --fd', 'bar', 'baz', 'qux'])
                self.assertFalse(mock_logger_warn.called)

            # with shell_args but not shell
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][2])
                self.assertEqual(formatted_args, ['foo', '--fd'])
                self.assertTrue(mock_logger_warn.called)

            # force win
            circus.process.IS_WINDOWS = True

            # without shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][0])
                self.assertEqual(formatted_args, ['foo --fd'])
                self.assertFalse(mock_logger_warn.called)

            # with shell_args
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][1])
                self.assertEqual(formatted_args, ['foo --fd'])
                self.assertTrue(mock_logger_warn.called)

            # with shell_args but not shell
            with patch.object(logger, 'warn') as mock_logger_warn:
                formatted_args = load(conf['watchers'][2])
                self.assertEqual(formatted_args, ['foo', '--fd'])
                self.assertTrue(mock_logger_warn.called)
        finally:
            circus.process.IS_WINDOWS = IS_WINDOWS

    def test_include_wildcards(self):
        conf = get_config(_CONF['include'])
        watchers = conf['watchers']
        self.assertEqual(len(watchers), 4)

    def test_include_multiple_wildcards(self):
        conf = get_config(_CONF['multiple_wildcard'])
        watchers = conf['watchers']
        self.assertEqual(len(watchers), 3)

    @patch.object(logger, 'warn')
    def test_empty_include(self, mock_logger_warn):
        """https://github.com/circus-tent/circus/pull/473"""
        try:
            get_config(_CONF['empty_include'])
        except:  # noqa: E722
            self.fail('Non-existent includes should not raise')
        self.assertTrue(mock_logger_warn.called)

    def test_watcher_graceful_timeout(self):
        conf = get_config(_CONF['issue210'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()

    def test_plugin_priority(self):
        arbiter = Arbiter.load_from_config(_CONF['issue680'])
        watchers = arbiter.iter_watchers()
        self.assertEqual(watchers[0].priority, 30)
        self.assertEqual(watchers[0].name, 'plugin:myplugin')
        self.assertEqual(watchers[1].priority, 20)
        self.assertEqual(watchers[1].cmd, 'sleep 20')
        self.assertEqual(watchers[2].priority, 10)
        self.assertEqual(watchers[2].cmd, 'sleep 10')

    def test_hooks(self):
        conf = get_config(_CONF['hooks'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEqual(watcher.hooks['before_start'].__doc__, hook.__doc__)
        self.assertTrue('before_start' not in watcher.ignore_hook_failure)

    def test_find_hook_in_pythonpath(self):
        arbiter = Arbiter.load_from_config(_CONF['find_hook_in_pythonpath'])
        watcher = arbiter.iter_watchers()[0]
        self.assertEqual(watcher.hooks['before_start'].__doc__,
                         'relative_hook')
        self.assertTrue('before_start' not in watcher.ignore_hook_failure)

    def test_watcher_env_var(self):
        conf = get_config(_CONF['env_var'])
        watcher = Watcher.load_from_config(conf['watchers'][0])
        self.assertEqual("%s:/bin" % os.getenv('PATH'), watcher.env['PATH'])
        watcher.stop()

    def test_env_section(self):
        conf = get_config(_CONF['env_section'])
        watchers_conf = {}
        for watcher_conf in conf['watchers']:
            watchers_conf[watcher_conf['name']] = watcher_conf
        watcher1 = Watcher.load_from_config(watchers_conf['watcher1'])
        watcher2 = Watcher.load_from_config(watchers_conf['watcher2'])

        self.assertEqual('lie', watcher1.env['CAKE'])
        self.assertEqual('cake', watcher2.env['LIE'])

        for watcher in [watcher1, watcher2]:
            self.assertEqual("%s:/bin" % os.getenv('PATH'),
                             watcher.env['PATH'])

        self.assertEqual('test1', watcher1.env['TEST1'])
        self.assertEqual('test1', watcher2.env['TEST1'])

        self.assertEqual('test2', watcher1.env['TEST2'])
        self.assertEqual('test2', watcher2.env['TEST2'])

        self.assertEqual('test3', watcher1.env['TEST3'])
        self.assertEqual('test3', watcher2.env['TEST3'])

    def test_issue395(self):
        conf = get_config(_CONF['issue395'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['graceful_timeout'], 88)

    def test_pidfile(self):
        conf = get_config(_CONF['circus'])
        self.assertEqual(conf['pidfile'], 'pidfile')

    def test_logoutput(self):
        conf = get_config(_CONF['circus'])
        self.assertEqual(conf['logoutput'], 'logoutput')

    def test_loglevel(self):
        conf = get_config(_CONF['circus'])
        self.assertEqual(conf['loglevel'], 'debug')

    def test_override(self):
        conf = get_config(_CONF['multiple_wildcard'])
        watchers = conf['watchers']
        self.assertEqual(len(watchers), 3)
        watchers = conf['watchers']
        watchers = sorted(watchers, key=lambda a: a['__name__'])
        self.assertEqual(watchers[2]['env']['INI'], 'private.ini')
        self.assertEqual(conf['check_delay'], 555)

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
        https://github.com/circus-tent/circus/pull/554
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

    def test_env_casesense(self):
        # #730 make sure respect case
        conf = get_config(_CONF['env_sensecase'])
        w = conf['watchers'][0]
        self.assertEqual(w['name'], 'webapp')
        self.assertTrue('http_proxy' in w['env'])
        self.assertEqual(w['env']['http_proxy'], 'http://localhost:8080')

        self.assertTrue('HTTPS_PROXY' in w['env'])
        self.assertEqual(w['env']['HTTPS_PROXY'], 'http://localhost:8043')

        self.assertTrue('FunKy_soUl' in w['env'])
        self.assertEqual(w['env']['FunKy_soUl'], 'scorpio')

    def test_issue567(self):
        os.environ['GRAVITY'] = 'down'
        conf = get_config(_CONF['issue567'])

        # make sure the global environment makes it into the cfg environment
        # even without [env] section
        self.assertEqual(conf['watchers'][0]['cmd'], 'down')

    def test_watcher_stop_signal(self):
        conf = get_config(_CONF['issue594'])
        self.assertEqual(conf['watchers'][0]['stop_signal'], signal.SIGINT)
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()

    def test_socket_so_reuseport_yes(self):
        conf = get_config(_CONF['reuseport'])
        s1 = conf['sockets'][1]
        self.assertEqual(s1['so_reuseport'], True)

    def test_socket_so_reuseport_no(self):
        conf = get_config(_CONF['reuseport'])
        s1 = conf['sockets'][0]
        self.assertEqual(s1['so_reuseport'], False)

    def test_check_delay(self):
        conf = get_config(_CONF['issue651'])
        self.assertEqual(conf['check_delay'], 10.5)

    def test_virtualenv(self):
        conf = get_config(_CONF['virtualenv'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['virtualenv'], "/tmp/.virtualenvs/test")
        self.assertEqual(watcher['virtualenv_py_ver'], "3.3")

    def test_empty_section(self):
        conf = get_config(_CONF['empty_section'])
        self.assertEqual([], conf.get('sockets'))
        self.assertEqual([], conf.get('plugins'))

    def test_issue1088(self):
        # #1088 - graceful_timeout should be float
        conf = get_config(_CONF['issue1088'])
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['graceful_timeout'], 25.5)
        watcher = Watcher.load_from_config(conf['watchers'][0])
        watcher.stop()


test_suite = EasyTestSuite(__name__)
