from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Signal(Command):
    """Send a signal """

    name = "signal"

    options = [('', 'children', True, "Only signal children of the fly")]

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 2 or largs > 4:
            raise ArgumentError("number of arguments invalid")

        msg = "SIGNAL %s" % " ".join(args)
        if not opts.get("children", False):
            return msg
        return "%s children" % msg

    def execute(self, trainer, args):
        signum, args = self._get_signal(args)
        show = self._get_show(trainer, args[0])
        try:
            if len(args) == 3:
                if args[2] == "children":
                    show.send_signal_children(args[1], signum)
                else:
                    show.send_signal_child(args[1], args[2], signum)
            elif len(args) == 2:
                show.senf_signal(args[1], signum)
            else:
                show.send_signal_flies(signum)
        except (KeyError, OSError) as e:
            raise MessageError(str(e))
        return "ok"
