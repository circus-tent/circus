import unittest
import os
from circus.config import get_config


_CONF = os.path.join(os.path.dirname(__file__),
                     'issue137.ini')


class TestConfig(unittest.TestCase):

    def test_issue137(self):
        conf = get_config(_CONF)
        watcher = conf['watchers'][0]
        self.assertEqual(watcher['uid'], 'me')
