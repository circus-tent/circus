import unittest

from circus.commands.util import validate_option
from circus.exc import MessageError


class TestValidateOption(unittest.TestCase):

    def test_uidgid(self):
        self.assertRaises(MessageError, validate_option, 'uid', {})
        validate_option('uid', 1)
        validate_option('uid', 'user')
        self.assertRaises(MessageError, validate_option, 'gid', {})
        validate_option('gid', 1)
        validate_option('gid', 'user')
