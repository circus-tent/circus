from __future__ import unicode_literals
import tempfile
import shutil
import os
import sys

try:
    import grp
    import pwd
except ImportError:
    grp = None
    pwd = None

import psutil
from psutil import Popen
from unittest import mock

from circus.tests.support import (TestCase, EasyTestSuite, skipIf,
                                  IS_WINDOWS, SLEEP)

from circus import util
from circus.util import (
    get_info, bytes2human, human2bytes, to_bool, parse_env_str, env_to_str,
    to_uid, to_gid, replace_gnu_args, get_python_version, load_virtualenv,
    get_working_dir
)


class TestUtil(TestCase):

    def setUp(self):
        self.dirs = []

    def tearDown(self):
        for dir in self.dirs:
            if os.path.exists(dir):
                shutil.rmtree(dir)

    def test_get_info(self):
        worker = Popen(["python", "-c", SLEEP % 5])
        try:
            info = get_info(worker)
        finally:
            worker.terminate()

        self.assertTrue(isinstance(info['pid'], int))

        if IS_WINDOWS:
            self.assertEqual(info['nice'], psutil.NORMAL_PRIORITY_CLASS)
        else:
            self.assertEqual(info['nice'], 0)

    def test_get_info_still_works_when_denied_access(self):
        def access_denied():
            return mock.MagicMock(side_effect=util.AccessDenied)

        class WorkerMock(mock.MagicMock):
            def __getattr__(self, attr):
                # this attr is accessed during the initialization
                # of the MagicMock, so we cannot raise here
                if attr == "_mock_methods":
                    return None

                raise util.AccessDenied()

        worker = WorkerMock()
        worker.get_memory_info = access_denied()
        worker.get_cpu_percent = access_denied()
        worker.get_cpu_times = access_denied()
        worker.get_nice = access_denied()
        worker.get_memory_percent = access_denied()
        worker.cmdline = []

        info = get_info(worker)

        self.assertEqual(info['mem'], 'N/A')
        self.assertEqual(info['cpu'], 'N/A')
        self.assertEqual(info['ctime'], 'N/A')
        self.assertEqual(info['pid'], 'N/A')
        self.assertEqual(info['username'], 'N/A')
        self.assertEqual(info['nice'], 'N/A')
        self.assertEqual(info['create_time'], 'N/A')
        self.assertEqual(info['age'], 'N/A')

        worker.nice = mock.MagicMock(side_effect=util.NoSuchProcess(1234))
        self.assertEqual(get_info(worker)['nice'], 'Zombie')

    def test_convert_opt(self):
        self.assertEqual(util.convert_opt('env', {'key': 'value'}),
                         'key=value')
        self.assertEqual(util.convert_opt('test', None), '')
        self.assertEqual(util.convert_opt('test', 1), '1')

    def test_bytes2human(self):
        self.assertEqual(bytes2human(100), '100B')
        self.assertEqual(bytes2human(10000), '9.77K')
        self.assertEqual(bytes2human(100001221), '95.37M')
        self.assertEqual(bytes2human(1024 * 1024 * 2047), '2.00G')
        self.assertRaises(TypeError, bytes2human, '1')

    def test_human2bytes(self):
        self.assertEqual(human2bytes('1B'), 1)
        self.assertEqual(human2bytes('9K'), 9216)
        self.assertEqual(human2bytes('1129M'), 1183842304)
        self.assertEqual(human2bytes('67T'), 73667279060992)
        self.assertEqual(human2bytes('13P'), 14636698788954112)
        self.assertEqual(human2bytes('1.99G'), 2136746229)
        self.assertEqual(human2bytes('2.00G'), 2147483648)
        self.assertRaises(ValueError, human2bytes, '')
        self.assertRaises(ValueError, human2bytes, 'faoej')
        self.assertRaises(ValueError, human2bytes, '123KB')
        self.assertRaises(ValueError, human2bytes, '48')
        self.assertRaises(ValueError, human2bytes, '23V')
        self.assertRaises(TypeError, human2bytes, 234)

    def test_tobool(self):
        for value in ('True ', '1', 'true'):
            self.assertTrue(to_bool(value))

        for value in ('False', '0', 'false'):
            self.assertFalse(to_bool(value))

        for value in ('Fal', '344', ''):
            self.assertRaises(ValueError, to_bool, value)

    def test_parse_env_str(self):
        env = 'booo=2,test=1'
        parsed = parse_env_str(env)
        self.assertEqual(parsed, {'test': '1', 'booo': '2'})
        self.assertEqual(env_to_str(parsed), env)

    @skipIf(not pwd, "Pwd not supported")
    def test_to_uid(self):
        with mock.patch('pwd.getpwnam') as getpw:
            m = mock.Mock()
            m.pw_uid = '1000'
            getpw.return_value = m
            uid = to_uid('user')
            self.assertEqual('1000', uid)
            uid = to_uid('user')
            self.assertEqual('1000', uid)

    @skipIf(not grp, "Grp not supported")
    def test_to_uidgid(self):
        self.assertRaises(ValueError, to_uid, 'xxxxxxx')
        self.assertRaises(ValueError, to_gid, 'xxxxxxx')
        self.assertRaises(ValueError, to_uid, -12)
        self.assertRaises(ValueError, to_gid, -12)
        self.assertRaises(TypeError, to_uid, None)
        self.assertRaises(TypeError, to_gid, None)

    @skipIf(not pwd, "Pwd not supported")
    def test_to_uid_str(self):
        with mock.patch('pwd.getpwuid') as getpwuid:
            uid = to_uid('1066')
            self.assertEqual(1066, uid)
            getpwuid.assert_called_with(1066)

    @skipIf(not grp, "Grp not supported")
    def test_to_gid_str(self):
        with mock.patch('grp.getgrgid') as getgrgid:
            gid = to_gid('1042')
            self.assertEqual(1042, gid)
            getgrgid.assert_called_with(1042)

    @skipIf(not grp, "Grp not supported")
    def test_negative_uid_gid(self):
        # OSX allows negative uid/gid and throws KeyError on a miss. On
        # 32-bit and 64-bit Linux, all negative values throw KeyError as do
        # requests for non-existent uid/gid.
        def int32(val):
            if val & 0x80000000:
                val += -0x100000000
            return val

        def uid_min_max():
            uids = sorted([int32(e[2]) for e in pwd.getpwall()])
            uids[0] = uids[0] if uids[0] < 0 else -1
            return uids[0], uids[-1]

        def gid_min_max():
            gids = sorted([int32(e[2]) for e in grp.getgrall()])
            gids[0] = gids[0] if gids[0] < 0 else -1
            return gids[0], gids[-1]

        uid_min, uid_max = uid_min_max()
        gid_min, gid_max = gid_min_max()

        def getpwuid(pid): return pwd.getpwuid(pid)

        def getgrgid(gid): return grp.getgrgid(gid)

        self.assertRaises(KeyError, getpwuid, uid_max + 1)
        self.assertRaises(KeyError, getpwuid, uid_min - 1)
        # getgrid may raises overflow error on mac/os x, fixed in python2.7.5
        # see http://bugs.python.org/issue17531
        self.assertRaises((KeyError, OverflowError), getgrgid, gid_max + 1)
        self.assertRaises((KeyError, OverflowError), getgrgid, gid_min - 1)

    def test_replace_gnu_args(self):
        repl = replace_gnu_args

        self.assertEqual('dont change --fd ((circus.me)) please',
                         repl('dont change --fd ((circus.me)) please'))

        self.assertEqual('dont change --fd $(circus.me) please',
                         repl('dont change --fd $(circus.me) please'))

        self.assertEqual('thats an int 2',
                         repl('thats an int $(circus.me)',
                              me=2))

        self.assertEqual('foobar', replace_gnu_args('$(circus.test)',
                         test='foobar'))
        self.assertEqual('foobar', replace_gnu_args('$(circus.test)',
                         test='foobar'))
        self.assertEqual('foo, foobar, baz',
                         replace_gnu_args('foo, $(circus.test), baz',
                                          test='foobar'))
        self.assertEqual('foo, foobar, baz',
                         replace_gnu_args('foo, ((circus.test)), baz',
                                          test='foobar'))

        self.assertEqual('foobar', replace_gnu_args('$(cir.test)',
                                                    prefix='cir',
                                                    test='foobar'))

        self.assertEqual('foobar', replace_gnu_args('((cir.test))',
                                                    prefix='cir',
                                                    test='foobar'))

        self.assertEqual('thats an int 2',
                         repl('thats an int $(s.me)', prefix='s',
                              me=2))

        self.assertEqual('thats an int 2',
                         repl('thats an int ((s.me))', prefix='s',
                              me=2))

        self.assertEqual('thats an int 2',
                         repl('thats an int $(me)', prefix=None,
                              me=2))

        self.assertEqual('thats an int 2',
                         repl('thats an int ((me))', prefix=None,
                              me=2))

    def test_get_python_version(self):
        py_version = get_python_version()

        self.assertEqual(3, len(py_version))

        for x in py_version:
            self.assertEqual(int, type(x))

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

        py_ver = sys.version.split()[0][:3]
        site_pkg = os.path.join(watcher.virtualenv, 'lib',
                                'python%s' % py_ver, 'site-packages')
        os.makedirs(site_pkg)
        watcher.env = {}
        load_virtualenv(watcher)
        self.assertEqual(site_pkg, watcher.env['PYTHONPATH'])

        # test with a specific python version for the virtualenv site packages
        py_ver = "my_python_version"
        site_pkg = os.path.join(watcher.virtualenv, 'lib',
                                'python%s' % py_ver, 'site-packages')
        os.makedirs(site_pkg)
        watcher.env = {}
        load_virtualenv(watcher, py_ver=py_ver)
        self.assertEqual(site_pkg, watcher.env['PYTHONPATH'])

    @mock.patch('circus.util.os.environ', {'PWD': '/path/to/pwd'})
    @mock.patch('circus.util.os.getcwd', lambda: '/path/to/cwd')
    def test_working_dir_return_pwd_when_paths_are_equals(self):
        def _stat(path):
            stat = mock.MagicMock()
            stat.ino = 'path'
            stat.dev = 'dev'
            return stat
        _old_os_stat = util.os.stat
        try:
            util.os.stat = _stat

            self.assertEqual(get_working_dir(), '/path/to/pwd')
        finally:
            util.os.stat = _old_os_stat


test_suite = EasyTestSuite(__name__)
