from circus.commands.base import Command
from circus.exc import ArgumentError


class RmWatcher(Command):
    """\
        Remove a watcher
        ================

        This command remove a watcher dynamically from the arbiter. The
        watchers are gracefully stopped.

        ZMQ Message
        -----------

        ::

            {
                "command": "rm",
                "properties": {
                    "name": "<nameofwatcher>",
                    "waiting": False
                }
            }

        The response return a status "ok".

        If ``waiting`` is False (default), the call will return immediatly
        after starting to remove and stop the corresponding watcher.

        If ``waiting`` is True, the call will return only when the remove and
        stop process is completly ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.

        Command line
        ------------

        ::

            $ circusctl rm <name> [--waiting]

        Options
        +++++++

        - <name>: name of the watcher to remove

    """

    name = "rm"
    properties = ['name']
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        self._get_watcher(arbiter, props['name'])
        return arbiter.rm_watcher(props['name'])
