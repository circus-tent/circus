import time

from circus.commands.base import Command, ok
from circus.exc import ArgumentError, MessageError

class AddShow(Command):
    """Add a show"""

    name = "add"
    options = [('', 'start', False, "start immediately the show")]
    properties = ['name', 'cmd']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")

        msg = self.make_message(name=args[0], cmd=" ".join(args[1:]))
        if opts.get("start", False):
            return [msg, self.make_message(command="start", name=args[0])]
        return msg

    def execute(self, trainer, props):
        trainer.add_show(props['name'], props['cmd'])
