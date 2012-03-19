from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class NumFlies(Command):
    """Get the number of flies"""

    name = "numflies"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return "NUMFLIES %s" % args[0]
        else:
            return "NUMFLIES"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            return str(show.numflies)
        else:
            return str(trainer.numflies())
