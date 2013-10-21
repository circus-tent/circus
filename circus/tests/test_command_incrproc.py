from circus.tests.support import TestCircus, EasyTestSuite
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


class FakeLoop(object):
    def add_callback(self, function):
        function()


class FakeArbiter(object):

    watcher_class = FakeWatcher

    def __init__(self):
        self.watchers = [self.watcher_class()]
        self.loop = FakeLoop()

    def get_watcher(self, name):
        return self.watchers[0]

    def stop_watchers(self, **options):
        self.watchers[:] = []

    def stop(self, **options):
        self.stop_watchers(**options)


class IncrProcTest(TestCircus):

    def test_incr_proc_message(self):
        cmd = IncrProc()
        message = cmd.message('dummy')
        self.assertTrue(message['properties'], {'name': 'dummy'})

        message = cmd.message('dummy', 3)
        props = sorted(message['properties'].items())
        self.assertEqual(props, [('name', 'dummy'), ('nb', 3)])

    def test_incr_proc(self):
        cmd = IncrProc()
        arbiter = FakeArbiter()
        size_before = arbiter.watchers[0].nb

        props = cmd.message('dummy', 3)['properties']
        cmd.execute(arbiter, props)
        self.assertEqual(arbiter.watchers[0].nb, size_before + 3)

test_suite = EasyTestSuite(__name__)
