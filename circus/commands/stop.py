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
                }
            }

        The response returns the status "ok".

        If the ``name`` property is present, then the stop will be applied
        to the watcher corresponding to that name. Otherwise, all watchers
        will get stopped.

        Command line
        ------------

        ::

            $ circusctl stop [<name>]

        Options
        +++++++

        - <name>: name of the watcher
    """

    name = "stop"
    callback = True

    def message(self, *args, **opts):
        if len(args) >= 1:
            return self.make_message(name=args[0], **opts)
        return self.make_message(**opts)

    def execute_with_cb(self, arbiter, props, callback):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.stop_with_cb(callback)
        else:
            arbiter.stop_watchers()
