from circus.commands.base import Command, check_is_graceful
from circus.exc import ArgumentError, MessageError

class Stop(Command):
    """\
        Stop a show or all shows gracefully or not
    """

    name = "stop"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            msg = "STOP %s" % args[0]
        else:
            msg = "STOP"

        if not opts.get("terminate", False):
            return "%s graceful" % msg

    def execute(self, trainer, args):
        args, graceful = check_is_graceful(args)
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            show.stop(graceful=graceful)
        else:
            trainer.stop_shows(graceful=graceful)
        return "ok"
