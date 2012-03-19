from circus.commands.base import Command
from circus.exc import MessageError

class Quit(Command):
    """\
        Quit the trainer immediately.
    """

    name = "quit"
    options = [('', 'terminate', False, "quit immediately")]

    def message(self, *args, **opts):
        graceful = not opts.get("terminate")
        return self.make_message(graceful=graceful)

    def execute(self, trainer, opts):
        trainer.stop(graceful=opts.get('graceful', True))
