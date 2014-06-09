import tempfile
import os
import shlex
import subprocess

from circus.pidfile import Pidfile
from circus.tests.support import TestCase, EasyTestSuite, SLEEP, IS_WINDOWS


class TestPidfile(TestCase):
    def test_pidfile(self):
        cmd = shlex.split(SLEEP % 120, posix=not IS_WINDOWS)
        proc = subprocess.Popen(cmd, shell=True)
        fd, path = tempfile.mkstemp()
        os.close(fd)

        try:
            pidfile = Pidfile(path)

            pidfile.create(proc.pid)
            self.assertRaises(RuntimeError, pidfile.create, proc.pid)
            pidfile.unlink()
            pidfile.create(proc.pid)
            pidfile.rename(path + '.2')
            self.assertTrue(os.path.exists(path + '.2'))
            self.assertFalse(os.path.exists(path))
        finally:
            os.remove(path + '.2')

test_suite = EasyTestSuite(__name__)
