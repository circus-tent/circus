import signal
import copy
import textwrap
import time

from circus.exc import MessageError

KNOWN_COMMANDS = []


def get_commands():
    commands = {}
    for c in KNOWN_COMMANDS:
        cmd = c()
        commands[c.name] = cmd.copy()
    return commands

def ok(props=None):
    resp = {"status": "ok", "time": time.time()}
    if props:
        resp.update(props)
    return resp

def error(reason="unknown", tb=None):
    return {
        "status": "error",
        "reason": reason,
        "tb": tb,
        "time": time.time()
    }

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
        desc  = textwrap.dedent(cls.__doc__).strip()
        setattr(cls, "desc",  desc)
        setattr(cls, "short", desc.splitlines()[0])


class Command(object):

    name = None
    msg_type = "dealer"
    options = []
    properties = []

    def make_message(self, **props):
        name = props.pop("command", self.name)
        return {"command": name, "properties": props or {}}

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

    def _get_signal(self, sig):
        if sig.lower() in ('quit', 'hup', 'kill', 'term', 'ttin', 'ttou'):
            return getattr(signal, "SIG%s" % sig.upper())
        raise ArgumentError("signal %r not supported" % args[-1])

    def validate(self, props):
        if not self.properties:
            return

        print props
        for propname in self.properties:
            if propname not in props:
                raise MessageError("message invalid %r is missing" %
                        propname)

Command = CommandMeta('Command', (Command,), {})
