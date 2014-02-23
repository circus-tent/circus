import copy
import textwrap
import time

from circus.exc import MessageError
from circus.commands import errors


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


def error(reason="unknown", tb=None, errno=errors.NOT_SPECIFIED):
    return {
        "status": "error",
        "reason": reason,
        "tb": tb,
        "time": time.time(),
        "errno": errno
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
        desc = textwrap.dedent(cls.__doc__).strip()
        setattr(cls, "desc",  desc)
        setattr(cls, "short", desc.splitlines()[0])


class Command(object):

    name = None
    msg_type = "dealer"
    options = []
    properties = []
    waiting = False
    waiting_options = [('waiting', 'waiting', False,
                        "Waiting the real end of the process")]

    ##################################################
    # These methods run within the circusctl process #
    ##################################################

    def make_message(self, **props):
        name = props.pop("command", self.name)
        return {"command": name, "properties": props or {}}

    def message(self, *args, **opts):
        raise NotImplementedError("message function isn't implemented")

    def console_error(self, msg):
        return "error: %s" % msg.get("reason")

    def console_msg(self, msg):
        if msg.get('status') == "ok":
            return "ok"
        return self.console_error(msg)

    def copy(self):
        return copy.copy(self)

    ################################################
    # These methods run within the circusd process #
    ################################################

    def execute(self, arbiter, props):
        raise NotImplementedError("execute function is not implemented")

    def _get_watcher(self, arbiter, watcher_name):
        """Get watcher from the arbiter if any."""
        try:
            return arbiter.get_watcher(watcher_name.lower())
        except KeyError:
            raise MessageError("program %s not found" % watcher_name)

    def validate(self, props):
        if not self.properties:
            return

        for propname in self.properties:
            if propname not in props:
                raise MessageError("message invalid %r is missing" % propname)


Command = CommandMeta('Command', (Command,), {})
