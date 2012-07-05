from circus.commands.base import Command
from circus.exc import ArgumentError


class Run(Command):
    """\
        Run a watcher
        ==============================

        This command runs the process in a watcher


        ZMQ Message
        -----------

        ::

            {
                "command": "run",
                "properties": {
                    "name": '<name>",
                }
            }

        The response return the status "ok".

        If the property name is present, the watcher will be run.

        Command line
        ------------

        ::

            $ circusctl run <name>

        Options
        +++++++

        - <name>: name of the watcher

    """
    name = "run"

    def message(self, *args, **opts):
        if len(args) != 1:
            raise ArgumentError("invalid number of arguments")

        return self.make_message(name=args[0])
    
    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.run()