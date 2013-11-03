from circus.commands.base import Command


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
                    "waiting": False
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


        Command line
        ------------

        ::

            $ circusctl stop [<name>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
    """

    name = "stop"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) >= 1:
            return self.make_message(name=args[0], **opts)
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            return watcher.stop()
        else:
            return arbiter.stop_watchers()
