from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class RmShow(Command):
    """Remove a show"""

    name = "rm"
    options = [('', 'terminate', False, "stop immediately")]
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("number of arguments invalid")

        graceful = not opts.get("terminate", False)
        return self.make_message(name=args[0], graceful=graceful)

    def execute(self, trainer, args):
        trainer.rm_show(args['name'])
