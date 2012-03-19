from circus.commands.base import Command, check_is_graceful
from circus.exc import MessageError

class Quit(Command):
    """\
        Quit the trainer immediately.
    """

    name = "quit"
    options = [('', 'terminate', False, "quit immediately")]

    def message(self, *args, **opts):
        if not opts.get("terminate"):
            return "QUIT graceful"
        return "QUIT"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("invalid number of arguments")

        args, graceful = check_is_graceful(args)
        trainer.stop(graceful=graceful)
        return "ok"
