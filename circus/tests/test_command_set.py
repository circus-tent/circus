from circus.tests.support import TestCircus
from circus.tests.test_command_incrproc import FakeArbiter as _FakeArbiter
from circus.commands.set import Set


class FakeWatcher(object):
    actions = []
    options = {}

    def set_opt(self, key, val):
        self.options[key] = val

    def do_action(self, action, callback):
        self.actions.append(action)


class FakeArbiter(_FakeArbiter):
    watcher_class = FakeWatcher


class SetTest(TestCircus):

    def test_set_stream(self):
        arbiter = FakeArbiter()
        cmd = Set()

        # setting streams
        props = cmd.message('dummy', 'stdout_stream.class', 'FileStream')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options,
                         {'stdout_stream.class': 'FileStream'})
        self.assertEqual(watcher.actions, [0])

        # setting hooks
        props = cmd.message('dummy', 'hooks.before_start', 'some.hook')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options['hooks.before_start'],
                         'some.hook')
        self.assertEqual(watcher.actions, [0, 0])

        # we can also set several hooks at once
        props = cmd.message('dummy', 'hooks',
                            'before_start:some,after_start:hook')
        props = props['properties']
        cmd.execute(arbiter, props)
        watcher = arbiter.watchers[0]
        self.assertEqual(watcher.options['hooks.before_start'],
                         'some')
        self.assertEqual(watcher.options['hooks.after_start'],
                         'hook')
