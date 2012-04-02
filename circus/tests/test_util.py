import grp
import os
import platform
import pwd
import unittest
from psutil import Popen

from circus.util import (get_info, bytes2human, to_bool, parse_env,
                         env_to_str, to_uid, to_gid)


class TestUtil(unittest.TestCase):

    def test_get_info(self):

        worker = Popen(["python -c 'import time;time.sleep(5)'"], shell=True)
        try:
            info = get_info(worker)
        finally:
            worker.terminate()

        self.assertTrue(isinstance(info['pid'], int))
        self.assertEqual(info['nice'], 0)

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

    def test_parse_env(self):
        env = 'test=1,booo=2'
        parsed = parse_env(env)
        self.assertEqual(env_to_str(parsed), env)

    def test_to_uidgid(self):
        self.assertRaises(ValueError, to_uid, 'xxxxxxx')
        self.assertRaises(ValueError, to_gid, 'xxxxxxx')
        self.assertRaises(ValueError, to_uid, -12)
        self.assertRaises(ValueError, to_gid, -12)
        self.assertRaises(TypeError, to_uid, None)
        self.assertRaises(TypeError, to_gid, None)

    def test_negative_uid_gid(self):
        # OSX allows negative uid/gid and throws KeyError on a miss.  On
        # x86_64 Linux, the range is (-1, 2^32-1), throwing OverflowError
        # outside that range, and KeyError on a miss. On 32-bit Linux, all
        # negative values throw KeyError as do requests for non-existent
        # uid/gid.
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

        if os.uname()[0] == 'Linux' and platform.machine() == 'x86_64':
            self.assertRaises(KeyError, getpwuid, uid_max + 1)
            self.assertRaises(OverflowError, getpwuid, uid_min - 1)
            self.assertRaises(KeyError, getgrgid, gid_max + 1)
            self.assertRaises(OverflowError, getgrgid, gid_min - 1)
        else:
            self.assertRaises(KeyError, getpwuid, uid_max + 1)
            self.assertRaises(KeyError, getpwuid, uid_min - 1)
            self.assertRaises(KeyError, getgrgid, gid_max + 1)
            self.assertRaises(KeyError, getgrgid, gid_min - 1)
