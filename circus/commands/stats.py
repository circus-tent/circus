from circus.exc import MessageError, ArgumentError
from circus.commands.base import Command

_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


class Stats(Command):
    """\
       Get process infos
       =================

       You can get at any time some statistics about your processes
       with the stat command.

       ZMQ Message
       -----------

       To get stats for all watchers::

            {
                "command": "stats"
            }


       To get stats for a watcher::

            {
                "command": "stats",
                "properties": {
                    "name": <name>
                }
            }

       To get stats for a process::


            {
                "command": "stats",
                "properties": {
                    "name": <name>,
                    "process": <processid>
                }
            }

       The response retun an object per process with the property "info"
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
              "process": 5,
              "status": "ok",
              "time": 1332265655.897085
            }

       Command Line
       ------------

       ::

            $ circusctl stats [<watchername>] [<processid>]

        """

    name = "stats"

    def message(self, *args, **opts):
        if len(args) > 2:
            raise ArgumentError("message invalid")

        if len(args) == 2:
            return self.make_message(name=args[0], process=int(args[1]))
        elif len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            if 'process' in props:
                try:
                    return {
                        "process": props['process'],
                        "info": watcher.process_info(props['process'])
                    }
                except KeyError:
                    raise MessageError("process %r not found in %r" % \
                            (props['process'], props['name']))
            else:
                return {"name": props['name'], "info": watcher.info()}
        else:
            infos = {}
            for watcher in arbiter.watchers:
                infos[watcher.name] = watcher.info()
            return {"infos": infos}

    def _to_str(self, info):
        if isinstance(info, basestring):
            return info

        children = info.pop("children", [])
        ret = [_INFOLINE % info]
        for child in children:
            ret.append("   " + _INFOLINE % child)
        return "\n".join(ret)

    def console_msg(self, msg):
        if msg['status'] == "ok":
            if "name" in msg:
                ret = ["%s:" % msg.get('name')]
                for process, info in msg.get('info', {}).items():
                    ret.append("%s: %s" % (process, self._to_str(info)))
                return "\n".join(ret)
            elif 'infos' in msg:
                ret = []
                for watcher, watcher_info in msg.get('infos', {}).items():
                    ret.append("%s:" % watcher)
                    watcher_info = watcher_info or {}
                    for process, info in watcher_info.items():
                        ret.append("%s: %s" % (process, self._to_str(info)))

                return "\n".join(ret)
            else:
                return "%s: %s\n" % (msg['process'], self._to_str(msg['info']))
        else:
            return self.console_error(msg)
