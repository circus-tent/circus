from tests.test_command_incrproc import FakeArbiter
from tests.support import TestCircus
from circus.commands.quit import Quit


class QuitTest(TestCircus):
    def test_quit(self):
        cmd = Quit()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].numprocesses, 1)
        props = cmd.message('dummy')['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(len(arbiter.watchers), 0)


