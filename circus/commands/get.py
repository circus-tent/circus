from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Get(Command):
    """Get the value of a show option"""

    name = "get"

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")
        return "GET %s %s" % (args[0], args[1])

    def execute(self, trainer, args):
        if len(args) < 2:
            raise MessageError("invalid number of parameters")

        show = self._get_show(trainer, args.pop(0))

        # get options values. It return an error if one of the asked
        # options isn't found
        ret = []
        for name in args:
            if name in show.optnames:
                val = show.get_opt(name)
                ret.append("%s: %s" % (name, val))
            else:
                return "error: %r option not found" % name
        return "\n".join(ret)
