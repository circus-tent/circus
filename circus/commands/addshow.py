from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class AddShow(Command):
    """Add a show"""

    name = "add"
    options = [('', 'start', True, "start immediately the show")]

    def message(self, *args, **opts):
        if len(args) < 2 or len(args) > 2:
            raise ArgumentError("number of arguments invalid")

        msg = "ADD %s %s" % (args[0], args[1])
        if opts.get("start", False):
            return [msg, "START %s" % args[0]]
        return msg

    def execute(self, trainer, args):
        if len(args) < 2:
            raise MessageError("message invalid")

        trainer.add_show(args[0], args[1])
        return "ok"
