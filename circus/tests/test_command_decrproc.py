from circus.tests.test_command_incrproc import FakeArbiter, FakeSingletonWatcher
from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.decrproc import DecrProcess


class DecrProcTest(TestCircus):

    def test_decr_proc(self):
        cmd = DecrProcess()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].numprocesses, 1)

        props = cmd.message('dummy')['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].numprocesses, 0)

    def test_decr_proc_singleton(self):
        cmd = DecrProcess()
        arbiter = FakeArbiter(watcher_class=FakeSingletonWatcher)
        size_before = arbiter.watchers[0].numprocesses

        props = cmd.message('dummy', 3)['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].numprocesses, size_before)


test_suite = EasyTestSuite(__name__)
