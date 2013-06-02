from circus.tests.support import TestCircus
from circus.commands.incrproc import IncrProc


class FakeWatcher(object):
    name = 'one'
    singleton = False
    nb = 1

    def info(self, *args):
        if len(args) == 1 and args[0] == 'meh':
            raise KeyError('meh')
        return 'yeah'

    process_info = info

    def incr(self, nb):
        self.nb += nb

    def decr(self, nb):
        self.nb -= nb


class FakeArbiter(object):
    watchers = [FakeWatcher()]

    def get_watcher(self, name):
        return self.watchers[0]


class IncrProcTest(TestCircus):

    def test_incr_proc_message(self):
        cmd = IncrProc()
        message = cmd.message('dummy')
        self.assertTrue(message['properties'], {'name': 'dummy'})

        message = cmd.message('dummy', 3)
        props = message['properties'].items()
        props.sort()
        self.assertEqual(props, [('name', 'dummy'), ('nb', 3)])

    def test_incr_proc(self):
        cmd = IncrProc()
        arbiter = FakeArbiter()
        self.assertTrue(arbiter.watchers[0].nb, 1)

        props = cmd.message('dummy', 3)['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].nb, 4)
