from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError


class Options(Command):
    """Get show options"""

    name = "options"

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return "OPTIONS %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        show = self._get_show(trainer, args[0])
        return "\n".join(["%s:%s" % (k, v) for k, v in show.options()])
