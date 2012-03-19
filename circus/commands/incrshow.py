from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class IncrShow(Command):
    """Increment the number of flies in a show"""

    name = "incr"
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")
        return self.make_message(name=args[0])

    def execute(self, trainer, props):
        show = self._get_show(trainer, props.get('name'))
        return {"numflies": show.incr()}
