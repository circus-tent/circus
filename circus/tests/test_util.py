import unittest
from circus.util import Popen


class TestUtil(unittest.TestCase):

    def test_get_info(self):

        worker = Popen(['top'], shell=True)
        try:
            info = worker.get_info()
        finally:
            worker.terminate()

        self.assertTrue(isinstance(info['pid'], int))
        self.assertEqual(info['nice'], 0)
