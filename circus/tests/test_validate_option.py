from circus.tests.support import TestCase, EasyTestSuite, IS_WINDOWS
from unittest.mock import patch

from circus.commands.util import validate_option
from circus.exc import MessageError


class TestValidateOption(TestCase):

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

        # make sure we control the hook names
        self.assertRaises(MessageError, validate_option, 'hooks',
                          {'IDONTEXIST': ['all', False]})

    def test_rlimit(self):
        if IS_WINDOWS:
            # rlimits are not supported on Windows
            self.assertRaises(MessageError, validate_option, 'rlimit_core', 1)
        else:
            validate_option('rlimit_core', 1)

            # require int parameter
            self.assertRaises(MessageError, validate_option,
                              'rlimit_core', '1')

            # require valid rlimit settings
            self.assertRaises(MessageError, validate_option, 'rlimit_foo', 1)


test_suite = EasyTestSuite(__name__)
