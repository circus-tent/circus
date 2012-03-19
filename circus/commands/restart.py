from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Restart(Command):
    """Restart the trainer or a show """

    name = "restart"

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
            show.restart()
        else:
            trainer.restart()
