from circus.exc import ArgumentError
from circus.commands.base import Command
from circus.util import get_info

_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


class Daemontats(Command):
    """\
       Get circusd stats
       =================

       You can get at any time some statistics about circusd
       with the dstat command.

       ZMQ Message
       -----------

       To get the circusd stats, simply run::

            {
                "command": "dstats"
            }


       The response returns a mapping the property "infos"
       containing some process informations::

            {
              "info": {
                "children": [],
                "cmdline": "python",
                "cpu": 0.1,
                "ctime": "0:00.41",
                "mem": 0.1,
                "mem_info1": "3M",
                "mem_info2": "2G",
                "nice": 0,
                "pid": 47864,
                "username": "root"
              },
              "status": "ok",
              "time": 1332265655.897085
            }

       Command Line
       ------------

       ::

            $ circusctl dstats

    """

    name = "dstats"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("Invalid message")
        return self.make_message()

    def execute(self, arbiter, props):
        return {'info': get_info(interval=0.01)}

    def _to_str(self, info):
        children = info.pop("children", [])
        ret = ['Main Process:',  '    ' + _INFOLINE % info]

        if len(children) > 0:
            ret.append('Children:')
            for child in children:
                ret.append('    ' + _INFOLINE % child)

        return "\n".join(ret)

    def console_msg(self, msg):
        if msg['status'] == "ok":
            return self._to_str(msg['info'])
        else:
            return self.console_error(msg)
