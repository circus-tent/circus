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
                    "async": True
                }
            }

        The response returns the status "ok".

        If the ``name`` property is present, then the stop will be applied
        to the watcher corresponding to that name. Otherwise, all watchers
        will get stopped.

        If ``async`` is True, processes will be killed in the background
        (defaults: False).  Otherwise the call will return immediatly after
        calling SIGTERM on each process and then, after a delay,
        asynchronously call SIGKILL on processes that are still up. The delay
        before SIGKILL can be configured using the
        :ref:`graceful_timeout option <graceful_timeout>`.


        Command line
        ------------

        ::

            $ circusctl stop [<name>] [--async]

        Options
        +++++++

        - <name>: name of the watcher
    """

    name = "stop"
    async = False

    def message(self, *args, **opts):
        if len(args) >= 1:
            return self.make_message(name=args[0], **opts)
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.stop(async=props.get('async', False))
        else:
            arbiter.stop_watchers(async=props.get('async', False))
