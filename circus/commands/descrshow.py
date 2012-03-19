from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError


class DecrShow(Command):
    """Decrement the number of flies in a show"""

    name = "decr"

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return "DECR %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        show = self._get_show(trainer, args[0])
        return str(show.decr())

