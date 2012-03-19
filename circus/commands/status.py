from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Status(Command):
    """Get the status of a show or all shows"""

    name = "status"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return "STATUS %s" % args[0]
        else:
            return "STATUS"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            return show.status()
        else:
            return trainer.statuses()
