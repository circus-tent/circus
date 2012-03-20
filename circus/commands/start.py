from circus.commands.base import Command
from circus.exc import ArgumentError


class Start(Command):
    """\
        Start the arbiter or a watcher
        ==============================

        This command start all the process in a watcher or all watchers.


        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "properties": {
                    "name": '<name>",
                }
            }

        The response return the status "ok".

        If the property name is present, the watcher will be started.

        Command line
        ------------

        ::

            $ circusctl start [<name>]

        Options
        +++++++

        - <name>: name of the watcher

    """
    name = "start"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.start()
        else:
            arbiter.start_watchers()
