from circus.commands.base import Command
from circus.exc import ArgumentError

class Start(Command):
    """Start a show or all shows"""

    name = "start"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            show.start()
        else:
            trainer.start_shows()
