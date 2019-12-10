import tempfile
import os
import stat
import subprocess

from circus.pidfile import Pidfile
from circus.tests.support import TestCase, EasyTestSuite, SLEEP


class TestPidfile(TestCase):
    def test_pidfile(self):
        proc = subprocess.Popen(SLEEP % 120, shell=True)
        fd, path = tempfile.mkstemp()
        os.close(fd)

        rf = path + '.2'
        try:
            pidfile = Pidfile(path)

            pidfile.create(proc.pid)
            mode = os.stat(path).st_mode
            self.assertEqual(stat.S_IMODE(mode), pidfile.perm_mode, path)
            pidfile.unlink()
            self.assertFalse(os.path.exists(path))
            pidfile.create(proc.pid)
            pidfile.rename(rf)
            self.assertTrue(os.path.exists(rf))
            self.assertFalse(os.path.exists(path))
            mode = os.stat(rf).st_mode
            self.assertEqual(stat.S_IMODE(mode), pidfile.perm_mode, rf)
        finally:
            os.remove(rf)

    def test_pidfile_data(self):
        proc = subprocess.Popen(SLEEP % 120, shell=True)
        fd, path = tempfile.mkstemp()

        os.write(fd, "fail-to-validate\n".encode('utf-8'))
        os.close(fd)

        try:
            pidfile = Pidfile(path)

            pidfile.create(proc.pid)
            self.assertTrue(os.path.exists(path))
            pid = 0
            with open(path, "r") as f:
                pid = int(f.read() or 0)
            self.assertEqual(pid, proc.pid)
        finally:
            os.remove(path)

        fd, path = tempfile.mkstemp()

        proc2 = subprocess.Popen(SLEEP % 0, shell=True)

        os.write(fd, "{0}\n".format(proc2.pid).encode('utf-8'))
        os.close(fd)

        proc2.wait()

        try:
            pidfile = Pidfile(path)

            self.assertNotEqual(proc2.pid, proc.pid)
            pidfile.create(proc.pid)
        finally:
            os.remove(path)

        fd, path = tempfile.mkstemp()

        os.write(fd, "fail-to-int\n".encode('utf-8'))
        os.close(fd)

        try:
            pidfile = Pidfile(path)

            pidfile.unlink()
            self.assertFalse(os.path.exists(path))
        except Exception as e:
            self.fail(str(e))


test_suite = EasyTestSuite(__name__)
