from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError


class Set(Command):
    """ Set a show option"""

    name = "set"

    def message(self, *args, **opts):
        if len(args) < 3:
            raise ArgumentError("number of arguments invalid")

        args = list(args)
        show_name = args.pop(0)
        if len(args) % 2 != 0:
            raise ArgumentError("List of key/values is invalid")

        return "SET %s %s" % (show_name, " ".join(args))

    def execute(self, trainer, args):
        if len(args) < 3:
            raise MessageError("invalid number of parameters")

        show = self._get_show(trainer, args.pop(0))
        if len(args) % 2 != 0:
            return  MessageError("List of key/values is invalid")

        # apply needed changes
        action = 0
        rest = args
        while len(rest) > 0:
            kv, rest = rest[:2], rest[2:]
            new_action = show.set_opt(kv[0], kv[1])
            if new_action == 1:
                action = 1

        # trigger needed action
        show.do_action(action)
