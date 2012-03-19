from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class List(Command):
    """ Get list of shows or flies in a show """

    name = "list"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return "LIST %s" % args[0]
        else:
            return "LIST"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            flies = sorted(show.flies)
            return ",".join([str(wid) for wid in flies])
        else:
            shows = sorted(trainer._shows_names)
            return ",".join([name for name in shows])
