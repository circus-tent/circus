import signal
import copy
import textwrap

from circus.exc import MessageError

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
        print "add %s" % new_class.__name__
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
