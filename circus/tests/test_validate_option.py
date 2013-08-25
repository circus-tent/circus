import unittest

from mock import patch

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

    @patch('warnings.warn')
    def test_stdout_stream(self, warn):
        self.assertRaises(
            MessageError, validate_option, 'stdout_stream', 'something')
        self.assertRaises(MessageError, validate_option, 'stdout_stream', {})
        validate_option('stdout_stream', {'class': 'MyClass'})
        validate_option(
            'stdout_stream', {'class': 'MyClass', 'my_option': '1'})
        validate_option(
            'stdout_stream', {'class': 'MyClass', 'refresh_time': 1})
        self.assertEqual(warn.call_count, 1)

    @patch('warnings.warn')
    def test_stderr_stream(self, warn):
        self.assertRaises(
            MessageError, validate_option, 'stderr_stream', 'something')
        self.assertRaises(MessageError, validate_option, 'stderr_stream', {})
        validate_option('stderr_stream', {'class': 'MyClass'})
        validate_option(
            'stderr_stream', {'class': 'MyClass', 'my_option': '1'})
        validate_option(
            'stderr_stream', {'class': 'MyClass', 'refresh_time': 1})
        self.assertEqual(warn.call_count, 1)

    def test_hooks(self):
        validate_option('hooks', {'before_start': ['all', False]})
