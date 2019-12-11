from circus.tests.support import TestCircus, EasyTestSuite
from circus.commands.stats import Stats, MessageError


_WANTED = """\
foo:
one: 1233  xx tarek false 132 132 13 123 xx
   1233  xx tarek false 132 132 13 123 xx
   1233  xx tarek false 132 132 13 123 xx"""


class FakeWatcher(object):
    name = 'one'

    def info(self, *args):
        if len(args) == 2 and args[0] == 'meh':
            raise KeyError('meh')
        return 'yeah'

    process_info = info


class FakeArbiter(object):
    watchers = [FakeWatcher()]

    def get_watcher(self, name):
        return FakeWatcher()


class StatsCommandTest(TestCircus):

    def test_console_msg(self):
        cmd = Stats()
        info = {'pid': '1233',
                'cmdline': 'xx',
                'username': 'tarek',
                'nice': 'false',
                'mem_info1': '132',
                'mem_info2': '132',
                'cpu': '13',
                'mem': '123',
                'ctime': 'xx'}

        info['children'] = [dict(info), dict(info)]

        res = cmd.console_msg({'name': 'foo',
                               'status': 'ok',
                               'info': {'one': info}})

        self.assertEqual(res, _WANTED)

    def test_execute(self):
        cmd = Stats()
        arbiter = FakeArbiter()
        res = cmd.execute(arbiter, {})
        self.assertEqual({'infos': {'one': 'yeah'}}, res)

        # info about a specific watcher
        props = {'name': 'one'}
        res = cmd.execute(arbiter, props)
        res = sorted(res.items())
        wanted = [('info', 'yeah'), ('name', 'one')]
        self.assertEqual(wanted, res)

        # info about a specific process
        props = {'process': '123', 'name': 'one'}
        res = cmd.execute(arbiter, props)
        res = sorted(res.items())
        wanted = [('info', 'yeah'), ('process', '123')]
        self.assertEqual(wanted, res)

        # info that breaks
        props = {'name': 'meh', 'process': 'meh'}
        self.assertRaises(MessageError, cmd.execute, arbiter, props)


test_suite = EasyTestSuite(__name__)
