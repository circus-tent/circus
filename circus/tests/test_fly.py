import unittest
import os
import sys
from circus.fly import Fly


class TestFly(unittest.TestCase):

    def test_base(self):
        cmd = "%s -c 'import time; time.sleep(2)'"
        fly = Fly('test', cmd % sys.executable, shell=True)
        try:
            info = fly.info()
            self.assertEqual(fly.pid, info['pid'])
            age = fly.age()
            self.assertTrue(age > 0.)
            self.assertFalse(fly.is_child(0))
        finally:
            fly.stop()
