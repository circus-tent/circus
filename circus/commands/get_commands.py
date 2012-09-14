from circus.commands.base import Command, get_commands


class GetCommands(Command):
    """
    """
    name = "get_commands"

    def execute(self, arbiter, props):
        return get_commands()

    def console_msg(self, msg):
        return ", ".join(msg)
