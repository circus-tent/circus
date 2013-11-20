from circus.commands.base import Command
from circus.exc import ArgumentError


class Spawn(Command):
    """\
        Spawn processes for the specified watcher.
        ==============================

        This command instructs the specified watcher to ensure that the
        configured (numprocesses) number of processes are spawned.  This can be
        used to bring all the processes for a watcher back up if automatic
        respawn was not enabled.


        ZMQ Message
        -----------

        ::

            {
                "command": "spawn",
                "properties": {
                    "name": '<name>",
                }
            }

        The request must include the name of the watcher that should spawn
        processes.

        The response returns the status "ok".

        Command line
        ------------

        ::

            $ circusctl spawn <name>

        Options
        +++++++

        - <name>: name of the watcher

    """
    name = "spawn"

    def message(self, *args, **opts):
        if len(args) != 1:
            raise ArgumentError("invalid number of arguments")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props['name'])
        return watcher.spawn_processes()
