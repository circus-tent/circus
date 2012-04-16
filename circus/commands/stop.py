from circus.commands.base import Command


class Stop(Command):
    """\
        Stop the arbiter or a watcher
        =============================

        This command stop all the process in a watcher or all watchers.

        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "propeties": {
                    "name": '<name>",
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the watcher.


        Command line
        ------------

        ::

            $ circusctl reload [<name>]

        Options
        +++++++

        - <name>: name of the watcher

    """

    name = "stop"

    def message(self, *args, **opts):
        return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.stop()
        else:
            arbiter.stop_watchers()
