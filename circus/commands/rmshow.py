from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class RmShow(Command):
    """Remove a show"""

    name = "rm"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("number of arguments invalid")

        if not opts.get("terminate", False):
            return "RM %s graceful" % args[0]
        else:
            return "RM %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1 or len(args) > 1:
            raise MessageError("message invalid")
        trainer.rm_show(args[0])
        return "ok"
