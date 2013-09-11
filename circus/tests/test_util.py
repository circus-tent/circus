from __future__ import unicode_literals
import tempfile
import grp
import pwd
import shutil
import os
import sys

from psutil import Popen
import mock

from circus.tests.support import unittest

from circus import util
from circus.util import (
    get_info, bytes2human, to_bool, parse_env_str, env_to_str,
    to_uid, to_gid, replace_gnu_args, get_python_version, load_virtualenv,
    get_working_dir
)


class TestUtil(unittest.TestCase):

    def setUp(self):
        self.dirs = []

    def tearDown(self):
        for dir in self.dirs:
            if os.path.exists(dir):
                shutil.rmtree(dir)

    def test_get_info(self):
        worker = Popen(["python -c 'import time;time.sleep(5)'"], shell=True)
        try:
            info = get_info(worker)
        finally:
            worker.terminate()

        self.assertTrue(isinstance(info['pid'], int))
        self.assertEqual(info['nice'], 0)

    def test_get_info_still_works_when_denied_access(self):
        def access_denied():
            return mock.MagicMock(side_effect=util.AccessDenied)

        class WorkerMock(mock.MagicMock):
            def __getattr__(self, attr):
                raise util.AccessDenied()

        worker = WorkerMock()
        worker.get_memory_info = access_denied()
        worker.get_cpu_percent = access_denied()
        worker.get_cpu_times = access_denied()
        worker.get_nice = access_denied()
        worker.get_memory_percent = access_denied()
        worker.cmdline = []

        info = get_info(worker)

        self.assertEquals(info['mem'], 'N/A')
        self.assertEquals(info['cpu'], 'N/A')
        self.assertEquals(info['ctime'], 'N/A')
        self.assertEquals(info['pid'], 'N/A')
        self.assertEquals(info['username'], 'N/A')
        self.assertEquals(info['nice'], 'N/A')
        self.assertEquals(info['create_time'], 'N/A')
        self.assertEquals(info['age'], 'N/A')

        worker.get_nice = mock.MagicMock(side_effect=util.NoSuchProcess(1234))
        self.assertEquals(get_info(worker)['nice'], 'Zombie')

    def test_convert_opt(self):
        self.assertEquals(util.convert_opt('env', {'key': 'value'}),
                          'key=value')
        self.assertEquals(util.convert_opt('test', None), '')
        self.assertEquals(util.convert_opt('test', 1), '1')

    def test_bytes2human(self):
        self.assertEqual(bytes2human(10000), '9K')
        self.assertEqual(bytes2human(100001221), '95M')
        self.assertRaises(TypeError, bytes2human, '1')

    def test_tobool(self):
        for value in ('True ', '1', 'true'):
            self.assertTrue(to_bool(value))

        for value in ('False', '0', 'false'):
            self.assertFalse(to_bool(value))

        for value in ('Fal', '344', ''):
            self.assertRaises(ValueError, to_bool, value)

    def test_parse_env_str(self):
        env = 'test=1,booo=2'
        parsed = parse_env_str(env)
        self.assertEqual(parsed, {'test': '1', 'booo': '2'})
        self.assertEqual(env_to_str(parsed), env)

    def test_to_uid(self):
        with mock.patch('pwd.getpwnam') as getpw:
            m = mock.Mock()
            m.pw_uid = '1000'
            getpw.return_value = m
            uid = to_uid(u'user')
            self.assertEqual('1000', uid)
            uid = to_uid('user')
            self.assertEqual('1000', uid)

    def test_to_uidgid(self):
        self.assertRaises(ValueError, to_uid, 'xxxxxxx')
        self.assertRaises(ValueError, to_gid, 'xxxxxxx')
        self.assertRaises(ValueError, to_uid, -12)
        self.assertRaises(ValueError, to_gid, -12)
        self.assertRaises(TypeError, to_uid, None)
        self.assertRaises(TypeError, to_gid, None)

    def test_negative_uid_gid(self):
        # OSX allows negative uid/gid and throws KeyError on a miss. On
        # 32-bit and 64-bit Linux, all negative values throw KeyError as do
        # requests for non-existent uid/gid.
        def int32(val):
            if (val & 0x80000000):
                val = -0x100000000 + val
            return val

        def uid_min_max():
            uids = sorted(map(lambda e: int32(e[2]), pwd.getpwall()))
            uids[0] = uids[0] if uids[0] < 0 else -1
            return (uids[0], uids[-1])

        def gid_min_max():
            gids = sorted(map(lambda e: int32(e[2]), grp.getgrall()))
            gids[0] = gids[0] if gids[0] < 0 else -1
            return (gids[0], gids[-1])

        uid_min, uid_max = uid_min_max()
        gid_min, gid_max = gid_min_max()

        getpwuid = lambda pid: pwd.getpwuid(pid)
        getgrgid = lambda gid: grp.getgrgid(gid)

        self.assertRaises(KeyError, getpwuid, uid_max + 1)
        self.assertRaises(KeyError, getpwuid, uid_min - 1)
        # getgrid may raises overflow error on mac/os x, fixed in python2.7.5
        # see http://bugs.python.org/issue17531
        self.assertRaises((KeyError, OverflowError), getgrgid, gid_max + 1)
        self.assertRaises((KeyError, OverflowError), getgrgid, gid_min - 1)

    def test_replace_gnu_args(self):
        repl = replace_gnu_args

        self.assertEquals('dont change --fd ((circus.me)) please',
                          repl('dont change --fd ((circus.me)) please'))

        self.assertEquals('dont change --fd $(circus.me) please',
                          repl('dont change --fd $(circus.me) please'))

        self.assertEquals('thats an int 2',
                          repl('thats an int $(circus.me)',
                               me=2))

        self.assertEquals('foobar', replace_gnu_args('$(circus.test)',
                          test='foobar'))
        self.assertEquals('foobar', replace_gnu_args('$(circus.test)',
                          test='foobar'))
        self.assertEquals('foo, foobar, baz',
                          replace_gnu_args('foo, $(circus.test), baz',
                                           test='foobar'))
        self.assertEquals('foo, foobar, baz',
                          replace_gnu_args('foo, ((circus.test)), baz',
                                           test='foobar'))

        self.assertEquals('foobar', replace_gnu_args('$(cir.test)',
                                                     prefix='cir',
                                                     test='foobar'))

        self.assertEquals('foobar', replace_gnu_args('((cir.test))',
                                                     prefix='cir',
                                                     test='foobar'))

        self.assertEquals('thats an int 2',
                          repl('thats an int $(s.me)', prefix='s',
                               me=2))

        self.assertEquals('thats an int 2',
                          repl('thats an int ((s.me))', prefix='s',
                               me=2))

        self.assertEquals('thats an int 2',
                          repl('thats an int $(me)', prefix=None,
                               me=2))

        self.assertEquals('thats an int 2',
                          repl('thats an int ((me))', prefix=None,
                               me=2))

    def test_get_python_version(self):
        py_version = get_python_version()

        self.assertEquals(3, len(py_version))

        map(lambda x: self.assertEquals(int, type(x)), py_version)

        self.assertGreaterEqual(py_version[0], 2)
        self.assertGreaterEqual(py_version[1], 0)
        self.assertGreaterEqual(py_version[2], 0)

    def _create_dir(self):
        dir = tempfile.mkdtemp()
        self.dirs.append(dir)
        return dir

    def test_load_virtualenv(self):
        watcher = mock.Mock()
        watcher.copy_env = False

        # we need the copy_env flag
        self.assertRaises(ValueError, load_virtualenv, watcher)

        watcher.copy_env = True
        watcher.virtualenv = 'XXX'

        # we want virtualenv to be a directory
        self.assertRaises(ValueError, load_virtualenv, watcher)

        watcher.virtualenv = self._create_dir()

        # we want virtualenv directory to contain a site-packages
        self.assertRaises(ValueError, load_virtualenv, watcher)

        minor = sys.version_info[1]
        site_pkg = os.path.join(watcher.virtualenv, 'lib',
                                'python2.%s' % minor, 'site-packages')
        os.makedirs(site_pkg)
        watcher.env = {}
        load_virtualenv(watcher)
        self.assertEqual(site_pkg, watcher.env['PYTHONPATH'])

    @mock.patch('circus.util.os.environ', {'PWD': '/path/to/pwd'})
    @mock.patch('circus.util.os.getcwd', lambda: '/path/to/cwd')
    def test_working_dir_return_pwd_when_paths_are_equals(self):
        def _stat(path):
            stat = mock.MagicMock()
            stat.ino = 'path'
            stat.dev = 'dev'
            return stat
        try:
            _old_os_stat = util.os.stat
            util.os.stat = _stat

            self.assertEquals(get_working_dir(), '/path/to/pwd')
        finally:
            util.os.stat = _old_os_stat
