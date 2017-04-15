from circus.commands.spawn import Spawn
from circus.exc import ArgumentError
from circus.tests.support import TestCircus, EasyTestSuite


class FakeWatcher(object):
    def __init__(self):
        self.running = 0
        self.numprocesses = 2

    def spawn_processes(self):
        self.running = self.numprocesses


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


class SpawnTest(TestCircus):
    def test_spawn(self):
        cmd = Spawn()
        arbiter = FakeArbiter()
        self.assertEqual(arbiter.watchers[0].running, 0)
        self.assertNotEqual(
            arbiter.watchers[0].running,
            arbiter.watchers[0].numprocesses)

        props = cmd.message('dummy')['properties']
        cmd.execute(arbiter, props)

        self.assertEqual(
            arbiter.watchers[0].running,
            arbiter.watchers[0].numprocesses)

    def test_exceptions(self):
        cmd = Spawn()
        with self.assertRaises(ArgumentError):
            cmd.message()

        with self.assertRaises(ArgumentError):
            cmd.message(1, 2)

test_suite = EasyTestSuite(__name__)
