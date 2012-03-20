from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class RmShow(Command):
    """\
        Remove a show
        =============

        This command remove a show dynamically from the trainer. The
        shows can be gracefully stopped.

        ZMQ Message
        -----------

        ::

            {
                "command": "rm",
                "properties": {
                    "name": "nameofshow",
                    "graceful": true
                }
            }

        A message contains 2 properties:

        - name: name of show
        - graceful: graceful stop

        The response return a status "ok".

        Command line
        ------------


        circusctl rm [--terminate] <name>
        Options
        +++++++

        - <name>: name of the show to create
        - --terminate; quit the node immediately

    """

    name = "rm"
    options = [('', 'terminate', False, "stop immediately")]
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("number of arguments invalid")

        graceful = not opts.get("terminate", False)
        return self.make_message(name=args[0], graceful=graceful)

    def execute(self, trainer, args):
        trainer.rm_show(args['name'])
