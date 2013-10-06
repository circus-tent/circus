from circus.tests.test_command_incrproc import FakeArbiter
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.decrproc import DecrProcess


class DecrProcTest(TestCircus):

    def test_decr_proc(self):
        cmd = DecrProcess()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].nb, 1)

        props = cmd.message('dummy')['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].nb, 0)

test_suite = EasyTestSuite(__name__)
