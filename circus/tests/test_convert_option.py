from circus.tests.support import unittest

from circus.commands.util import convert_option


class TestConvertOption(unittest.TestCase):

    def test_env(self):
        env = convert_option("env", {"port": "8080"})
        self.assertDictEqual({"port": "8080"}, env)

    def test_stdout_and_stderr_stream(self):
        expected_convertions = (
            ('stdout_stream.class', 'class', 'class'),
            ('stdout_stream.filename', 'file', 'file'),
            ('stdout_stream.other_option', 'other', 'other'),
            ('stdout_stream.refresh_time', '10', '10'),
            ('stdout_stream.max_bytes', '10', 10),
            ('stdout_stream.backup_count', '20', 20),
            ('stderr_stream.class', 'class', 'class'),
            ('stderr_stream.filename', 'file', 'file'),
            ('stderr_stream.other_option', 'other', 'other'),
            ('stderr_stream.refresh_time', '10', '10'),
            ('stderr_stream.max_bytes', '10', 10),
            ('stderr_stream.backup_count', '20', 20),
            ('stderr_stream.some_number', '99', '99'),
            ('stderr_stream.some_number_2', 99, 99),
        )

        for option, value, expected in expected_convertions:
            ret = convert_option(option, value)
            self.assertEqual(ret, expected)
