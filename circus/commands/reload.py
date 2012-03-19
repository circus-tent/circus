from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Reload(Command):
    """Reload the trainer or a show """

    name = "reload"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        graceful = not opts.get("terminate", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful)
        else:
            return self.make_message(graceful=graceful)

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            show.reload(graceful=props.get('graceful', True))
        else:
            trainer.reload(graceful=props.get('graceful', True))
