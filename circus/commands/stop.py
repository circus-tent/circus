from circus.commands.base import Command


class Stop(Command):
    """\
        Stop the arbiter or a watcher
        =============================

        This command stop all the process in a watcher or all watchers.
        The watchers can be stopped gracefully.

        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "propeties": {
                    "name": '<name>",
                    "graceful": true
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the processes will be exited gracefully.

        If the property name is present, then the reload will be applied
        to the watcher.


        Command line
        ------------

        ::

            $ circusctl reload [<name>] [--terminate]

        Options
        +++++++

        - <name>: name of the watcher
        - --terminate; quit the node immediately

    """

    name = "stop"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        graceful = not opts.get("terminate", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful)

        return self.make_message(graceful=graceful)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.stop(graceful=props.get('graceful', True))
        else:
            arbiter.stop_watchers(graceful=props.get('graceful', True))
