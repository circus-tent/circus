from circus.commands.base import Command
from circus.commands.restart import execute_watcher_start_stop_restart
from circus.commands.restart import match_options
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
                    "waiting": False,
                    "match": "[simple|glob|regex]"
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

        The ``match`` parameter can have the value ``simple`` for string
        compare, ``glob`` for wildcard matching (default) or ``regex`` for
        regex matching.


        Command line
        ------------

        ::

        $ circusctl restart [name] [--waiting] [--match=simple|glob|regex]

        Options
        +++++++

        - <name>: name or pattern of the watcher(s)
        - <match>: watcher match method

    """
    name = "start"
    options = list(Command.waiting_options)
    options.append(match_options)

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return execute_watcher_start_stop_restart(
            self, arbiter, props, 'start', arbiter.start_watchers,
            arbiter.start_watchers)
