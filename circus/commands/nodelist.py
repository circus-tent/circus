from circus.commands.base import Command
from circus.exc import ArgumentError


class NodeList(Command):
    name = "nodelist"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("message invalid")

        else:
            return self.make_message()

    def execute(self, arbiter, props):
        return {'nodes': arbiter.nodes}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("nodelist"))
        return self.console_error(msg)
