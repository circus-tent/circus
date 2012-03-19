from circus.commands.base import Command
from circus.exc import ArgumentError

class Start(Command):
    """Start a show or all shows"""

    name = "start"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return "START %s" % args[0]
        else:
            return "START"

    def execute(self, trainer, args):
        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            show.start()
        else:
            trainer.start_shows()
        return "ok"
