""" circus commands """

import copy
import textwrap

from circus.exc import ArgumentError, MessageError

KNOWN_COMMANDS = []

def get_commands():
    commands = {}
    for c in KNOWN_COMMANDS:
        cmd = c()
        commands[c.name] = cmd.copy()
    return commands


def check_is_graceful(args):
    if len(args) > 0 and args[-1] == "graceful":
        return args[:-1], True
    return args, False


class CommandMeta(type):

    def __new__(cls, name, bases, attrs):
        super_new = type.__new__
        parents = [b for b in bases if isinstance(b, CommandMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)
        attrs["order"] = len(KNOWN_COMMANDS)
        new_class = super_new(cls, name, bases, attrs)
        new_class.fmt_desc()
        KNOWN_COMMANDS.append(new_class)
        return new_class

    def fmt_desc(cls):
        setattr(cls, "desc", textwrap.dedent(cls.__doc__).strip())


class Command(object):

    name = None
    msg_type = "dealer"
    options = []

    def message(self, *args, **opts):
        raise NotImplementedError("message function isn't implemented")

    def execute(self, trainer, args):
        raise NotImplementedError("execute function not implemented")

    def copy(self):
        return copy.copy(self)

    def _get_show(self, trainer, show_name):
        """ get show from the trainer if any """
        try:
            return trainer.get_show(show_name.lower())
        except KeyError:
            raise MessageError("program %s not found" % show_name)

    def _get_signal(self, args):
        if args[-1].lower() in ('quit', 'hup', 'kill', 'term',):
            return args[:-1], getattr(signal, "SIG%s" % args[-1].upper())
        raise MessageError("signal %r not supported" % args[-1])


Command = CommandMeta('Command', (Command,), {})


#########################################
# commands
#########################################

class Quit(Command):
    """\
        quit the trainer immediately.
    """

    name = "quit"
    options = [('', 'terminate', False, "quit immediately")]

    def message(self, *args, **opts):
        if not opts.get("terminate"):
            print "ici"
            return "QUIT graceful"
        return "QUIT"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        args, graceful = check_is_graceful(args)
        trainer.stop(graceful=graceful)
        return "ok"


class Start(Command):
    """Start a show or all shows"""

    name = "start"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return "START %s" % args[0]
        else:
            return "START"

    def execute(self, trainer, args):
        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            show.start()
        else:
            trainer.start_shows()
        return "ok"

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

class Restart(Command):
    """restart the trainer or a show """

    name = "restart"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return "RESTART %s" % args[0]
        else:
            return "RESTART"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            show.restart()
        else:
            trainer.restart()
        return "ok"

class Reload(Command):
    """reload the trainer or a show """

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

class List(Command):
    """ Get list of shows or flies in a show """

    name = "list"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return "LIST %s" % args[1]
        else:
            return "LIST"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            flies = sorted(show.flies)
            return ",".join([str(wid) for wid in flies])
        else:
            shows = sorted(trainer._shows_names)
            return ",".join([name for name in shows])


class NumShows(Command):
    """Get the number of shows"""

    name = "numshows"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("invalid number of arguments")

        return "NUMSHOWS"

    def execute(self, trainer, args):
        if len(args) > 0:
            raise MessageError("message invalid")
        return str(trainer.numshows())


class NumFlies(Command):
    """Get the number of flies"""

    name = "numflies"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return "NUMFLIES %s" % args[0]
        else:
            return "NUMFLIES"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            return str(show.numflies)
        else:
            return str(trainer.numflies())


class Status(Command):
    """Get the status of a show or all shows"""

    name = "status"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return "STATUS %s" % args[0]
        else:
            return "STATUS"

    def execute(self, trainer, args):
        if len(args) > 1:
            raise MessageError("message invalid")

        if len(args) == 1:
            show = self._get_show(trainer, args[0])
            return show.status()
        else:
            return trainer.statuses()


class Stats(Command):
    """Get process infos"""

    name = "stats"

    def message(self, *args, **opts):
        if len(args) > 2:
            raise ArgumentError("message invalid")

        if len(args) == 2:
            return "STATS %s %s" % (args[0], args[1])
        elif len(args) == 1:
            return "STATS %s" % args[0]
        else:
            return "STATS"

    def execute(self, trainer, args):
        if len(args) > 2:
            raise MessageError("message invalid")

        if len(args) ==  2:
            show = self._get_show(trainer, args[0])
            try:
                return show.fly_info(args[1])
            except KeyError:
                raise MessageError("fly %r not found in %r" % (args[1],
                                    args[0]))

        elif len(args) == 1:
            show = self._get_show(trainer, args[0])
            return "\n".join(show.info())
        else:
            infos = []
            for show in trainer.shows:
                infos.append("%s:\n" % show.name)
                show_info = "\n".join(show.info())
                infos.append("%s\n" % show_info)
            return buffer("".join(infos))


class AddShow(Command):
    """Add a show"""

    name = "add"
    options = [('', 'start', True, "start immediately the show")]

    def message(self, *args, **opts):
        if len(args) < 2 or len(args) > 2:
            raise ArgumentError("number of arguments invalid")

        msg = "ADD %s %s" % (args[0], args[1])
        if opts.get("start", False):
            return [msg, "START %s" % args[0]]
        return msg

    def execute(self, trainer, args):
        if len(args) < 2:
            raise MessageError("message invalid")

        trainer.add_show(args[0], args[1])
        return "ok"


class RmShow(Command):
    """Remove a show"""

    name = "rm"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("number of arguments invalid")

        if not opts.get("terminate", False):
            return "RM %s graceful" % args[0]
        else:
            return "RM %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1 or len(args) > 1:
            raise MessageError("message invalid")
        trainer.rm_show(args[0])
        return "ok"


class IncrShow(Command):
    """Increment the number of flies in a show"""

    name = "incr"

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return "INCR %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        show = self._get_show(trainer, args[0])
        return str(show.incr())

class DecrShow(Command):
    """Decrement the number of flies in a show"""

    name = "decr"

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return "DECR %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        show = self._get_show(trainer, args[0])
        return str(show.decr())

class Options(Command):
    """Get show options"""

    name = "options"

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return "OPTIONS %s" % args[0]

    def execute(self, trainer, args):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        show = self._get_show(trainer, args[0])
        return "\n".join(["%s:%s" % (k, v) for k, v in show.options()])

class Set(Command):
    """ set a show option"""

    name = "set"

    def message(self, *args, **opts):
        if len(args) < 3:
            raise ArgumentError("number of arguments invalid")

        args = list(args)
        show_name = args.pop(0)
        if len(args) % 2 != 0:
            raise ArgumentError("List of key/values is invalid")

        return "SET %s %s" % (show_name, " ".join(args))

    def execute(self, trainer, args):
        if len(args) < 3:
            raise MessageError("invalid number of parameters")

        show = self._get_show(trainer, args.pop(0))
        if len(args) % 2 != 0:
            return  MessageError("List of key/values is invalid")

        # apply needed changes
        action = 0
        rest = args
        while len(rest) > 0:
            kv, rest = rest[:2], rest[2:]
            new_action = show.set_opt(kv[0], kv[1])
            if new_action == 1:
                action = 1

        # trigger needed action
        show.do_action(action)

class Get(Command):
    """Get the value of a show option"""

    name = "get"

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")
        return "GET %s %s" % (args[0], args[1])

    def execute(self, trainer, args):
        if len(args) < 2:
            raise MessageError("invalid number of parameters")

        show = self._get_show(trainer, args.pop(0))

        # get options values. It return an error if one of the asked
        # options isn't found
        ret = []
        for name in args:
            if name in show.optnames:
                val = show.get_opt(name)
                ret.append("%s: %s" % (name, val))
            else:
                return "error: %r option not found" % name
        return "\n".join(ret)

class Signal(Command):
    """Send a signal """

    name = "signal"

    options = [('', 'children', True, "Only signal children of the fly")]

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 2 or largs > 4:
            raise ArgumentError("number of arguments invalid")


        msg =  "SIGNAL %s" % " ".join(args)
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

class Listen(Command):
    """Suscribe to a show event"""

    name = "listen"
    msg_type = "sub"

    def message(self, *args, **opts):
        if not args:
            return [""]
        return list(args)

    def execute(self, trainer, args):
        raise MessageError("invalid message. use a pub/sub socket")
