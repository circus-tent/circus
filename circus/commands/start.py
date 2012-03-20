from circus.commands.base import Command
from circus.exc import ArgumentError

class Start(Command):
    """\
        Start the trainer or a show
        ===========================

        This command start all the fly in a show or all shows. T
        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "propeties": {
                    "name": '<name>",
                }
            }

        The response return the status "ok".

        If the property name is present, the show will be started.

        Command line
        ------------

        ::

            circusctl start [<name>]
        Options
        +++++++

        - <name>: name of the show

    """
    name = "start"

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
            show.start()
        else:
            trainer.start_shows()
