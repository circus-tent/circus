from circus.tests.support import unittest

from circus.commands.util import convert_option


class TestConvertOption(unittest.TestCase):

        def test_env(self):
            env = convert_option("env", {"port": "8080"})
            self.assertDictEqual({"port": "8080"}, env)
