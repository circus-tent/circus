from circus.tests.support import TestCircus
from circus.commands.stats import Stats

_WANTED = """\
foo:
one: 1233  xx tarek false 132 132 13 123 xx
   1233  xx tarek false 132 132 13 123 xx
   1233  xx tarek false 132 132 13 123 xx"""


class StatsCommandTest(TestCircus):

    def test_statst_watchers(self):
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
