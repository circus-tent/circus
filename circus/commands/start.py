from circus.commands.base import Command
from circus.commands.restart import execute_watcher_start_stop_restart
from circus.exc import ArgumentError


class Start(Command):
    """\
        Start the arbiter or a watcher
        ==============================

        This command starts all the processes in a watcher or all watchers.


        ZMQ Message
        -----------

        ::

            {
                "command": "start",
                "properties": {
                    "name": '<name>",
                    "waiting": False
                }
            }

        The response return the status "ok".

        If the property name is present, the watcher will be started.

        If ``waiting`` is False (default), the call will return immediately
        after calling `start` on each process.

        If ``waiting`` is True, the call will return only when the start
        process is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.

        Command line
        ------------

        ::

            $ circusctl start [<name>] --waiting

        Options
        +++++++

        - <name>: (wildcard) name of the watcher(s)

    """
    name = "start"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return execute_watcher_start_stop_restart(
            arbiter, props, 'start', arbiter.start_watchers,
            arbiter.start_watchers)
