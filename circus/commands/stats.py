from circus.exc import MessageError
from circus.commands.base import Command

_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")

class Stats(Command):
    """Get process infos"""

    name = "stats"

    def message(self, *args, **opts):
        if len(args) > 2:
            raise ArgumentError("message invalid")

        if len(args) == 2:
            return self.make_message(name=args[0], fly=int(args[1]))
        elif len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            if 'fly' in props:
                try:
                    return {
                        "fly": props['fly'],
                        "info": show.fly_info(props['fly'])
                    }
                except KeyError:
                    raise MessageError("fly %r not found in %r" % (props['fly'],
                        props['name']))
            else:
                return {"name": props['name'], "info": show.info()}
        else:
            infos = {}
            for show in trainer.shows:
                infos[show.name] = show.info()
            return {"infos": infos}

    def _to_str(self, info):
        children = info.pop("children", [])
        ret = [_INFOLINE % info]
        for child in children:
            ret.append("   " + _INFOLINE % child)
        return "\n".join(ret)

    def console_msg(self, msg):
        if msg['status'] == "ok":
            if "name" in msg:
                ret = ["%s:" % msg.get('name')]
                for fly, info in msg.get('info', {}).items():
                    ret.append("%s: %s" % (fly, self._to_str(info)))
                return "\n".join(ret)
            elif 'infos' in msg:
                ret = []
                for show, show_info in msg.get('infos', {}).items():
                    ret.append("%s:" % show)
                    show_info = show_info or {}
                    for fly, info in show_info.items():
                        ret.append("%s: %s" % (fly, self._to_str(info)))

                return "\n".join(ret)
            else:
                return "%s: %s\n" % (msg['fly'], self._to_str(msg['info']))
        else:
            return self.console_error(msg)



