import unittest
from psutil import Popen
from circus.util import get_info


class TestUtil(unittest.TestCase):

    def test_get_info(self):

        worker = Popen(["python -c 'import time;time.sleep(5)'"], shell=True)
        try:
            info = get_info(worker)
        finally:
            worker.terminate()

        self.assertTrue(isinstance(info['pid'], int))
        self.assertEqual(info['nice'], 0)
