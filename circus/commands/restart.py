from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Restart(Command):
    """\
        Restart the trainer or a show
        =============================

        This command restart all the fly in a show or all shows. This
        funtion simply stop a show then restart it.

        ZMQ Message
        -----------

        ::

            {
                "command": "restart",
                "propeties": {
                    "name": '<name>"
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the show.


        Command line
        ------------

        ::

            circusctl restart [<name>] [--terminate]

        Options
        +++++++

        - <name>: name of the show
        - --terminate; quit the node immediately

    """
    name = "restart"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            show.restart()
        else:
            trainer.restart()
