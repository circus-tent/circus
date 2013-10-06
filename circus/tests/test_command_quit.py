from circus.tests.test_command_incrproc import FakeArbiter
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.quit import Quit


class QuitTest(TestCircus):
    def test_quit(self):
        cmd = Quit()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].nb, 1)
        props = cmd.message('dummy')['properties']
        cmd.async_execute(arbiter, props)
        self.assertEqual(len(arbiter.watchers), 0)
        props['async'] = True

    def test_quit_async(self):
        cmd = Quit()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].nb, 1)
        props = cmd.message('dummy')['properties']
        props['async'] = True
        cmd.async_execute(arbiter, props)
        self.assertEqual(len(arbiter.watchers), 0)

test_suite = EasyTestSuite(__name__)
