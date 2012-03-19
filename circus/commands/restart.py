from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Restart(Command):
    """Restart the trainer or a show """

    name = "restart"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return "RESTART %s" % args[0]
        else:
            return "RESTART"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            show.restart()
        else:
            trainer.restart()
        return "ok"
