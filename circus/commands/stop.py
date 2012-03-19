from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Stop(Command):
    """\
        Stop a show or all shows gracefully or not
    """

    name = "stop"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        graceful = not opts.get("terminate", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful)
            msg = "STOP %s" % args[0]
        else:
            return self.make_message(graceful=graceful)

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            show.stop(graceful=props.get('graceful', True))
        else:
            trainer.stop_shows(graceful=props.get('graceful', True))
