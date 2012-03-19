from circus.commands.base import Command, check_is_graceful
from circus.exc import ArgumentError, MessageError

class Reload(Command):
    """Reload the trainer or a show """

    name = "reload"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            msg = "RELOAD %s" % args[0]
        else:
            msg = "RELOAD"

        if not opts.get("terminate", False):
            return "%s graceful" % msg

        return msg

    def execute(self, trainer, args):
        args, graceful = check_is_graceful(args)
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            show.reload(graceful=graceful)
        else:
            trainer.reload(graceful=graceful)
        return "ok"
