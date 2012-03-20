import time

from circus.commands.base import Command, ok
from circus.exc import ArgumentError, MessageError

class AddShow(Command):
    """\
        Add a show
        ==========

        This command add a show dynamically to a trainer.

        ZMQ Message
        -----------

        ::

            {
                "command": "add",
                "properties": {
                    "cmd": "/path/to/commandline --option"
                    "name": "nameofshow"
                }
            }

        A message contains 2 properties:

        - cmd: Full command line to execute in a fly
        - name: name of show

        The response return a status "ok".

        Command line
        ------------


        circusctl add [--start] <name> <cmd>

        Options
        +++++++

        - <name>: name of the show to create
        - <cmd>: ull command line to execute in a fly
        - --start: start the show immediately

    """

    name = "add"
    options = [('', 'start', False, "start immediately the show")]
    properties = ['name', 'cmd']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")

        msg = self.make_message(name=args[0], cmd=" ".join(args[1:]))
        if opts.get("start", False):
            return [msg, self.make_message(command="start", name=args[0])]
        return msg

    def execute(self, trainer, props):
        trainer.add_show(props['name'], props['cmd'])
