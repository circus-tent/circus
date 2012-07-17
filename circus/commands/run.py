from circus.commands.base import Command
from circus.exc import ArgumentError


class Run(Command):
    """\
        Run a watcher
        ==============================

        This command runs one watcher's process and does not try to control it
        in any way: it's a fire and forget thing.


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
    properties = ['name', ]

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props['name'])
        watcher.run()
