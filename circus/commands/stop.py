from circus.commands.base import Command
from circus.commands.restart import execute_watcher_start_stop_restart
from circus.commands.restart import match_options


class Stop(Command):
    """\
        Stop watchers
        =============

        This command stops a given watcher or all watchers.

        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "properties": {
                    "name": "<name>",
                    "waiting": False,
                    "match": "[simple|glob|regex]"
                }
            }

        The response returns the status "ok".

        If the ``name`` property is present, then the stop will be applied
        to the watcher corresponding to that name. Otherwise, all watchers
        will get stopped.

        If ``waiting`` is False (default), the call will return immediatly
        after calling `stop_signal` on each process.

        If ``waiting`` is True, the call will return only when the stop process
        is completly ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.

        The ``match`` parameter can have the value ``simple`` for string
        compare, ``glob`` for wildcard matching (default) or ``regex`` for
        regex matching.


        Command line
        ------------

        ::

            $ circusctl stop [name] [--waiting] [--match=simple|glob|regex]

        Options
        +++++++

        - <name>: name or pattern of the watcher(s)
        - <match>: watcher match method
    """

    name = "stop"
    options = list(Command.waiting_options)
    options.append(match_options)

    def message(self, *args, **opts):
        if len(args) >= 1:
            return self.make_message(name=args[0], **opts)
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return execute_watcher_start_stop_restart(
            self, arbiter, props, 'stop', arbiter.stop_watchers,
            arbiter.stop_watchers)
