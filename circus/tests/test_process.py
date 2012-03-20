import unittest
import sys
from circus.process import Process


class TestProcess(unittest.TestCase):

    def test_base(self):
        cmd = "%s -c 'import time; time.sleep(2)'"
        process = Process('test', cmd % sys.executable, shell=True)
        try:
            info = process.info()
            self.assertEqual(process.pid, info['pid'])
            age = process.age()
            self.assertTrue(age > 0.)
            self.assertFalse(process.is_child(0))
        finally:
            process.stop()
