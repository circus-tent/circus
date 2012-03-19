from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class NumFlies(Command):
    """Get the number of flies"""

    name = "numflies"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            return {
                "numflies": show.numflies,
                "show_name": props['name']
            }
        else:
            return {"numflies": trainer.numflies()}
