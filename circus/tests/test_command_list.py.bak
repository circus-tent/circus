from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.list import List


class ListCommandTest(TestCircus):

    def test_list_watchers(self):
        cmd = List()
        self.assertTrue(
            cmd.console_msg({'watchers': ['foo', 'bar']}),
            'foo,bar')

    def test_list_processors(self):
        cmd = List()
        self.assertTrue(
            cmd.console_msg({'pids': [12, 13]}), '12,13')

    def test_list_error(self):
        cmd = List()
        self.assertTrue("error" in cmd.console_msg({'foo': 'bar'}))


test_suite = EasyTestSuite(__name__)
