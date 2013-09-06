import unittest
import tempfile
import os
import subprocess

from circus.pidfile import Pidfile


class TestPidfile(unittest.TestCase):
    def test_pidfile(self):
        proc = subprocess.Popen('sleep 120', shell=True)
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
