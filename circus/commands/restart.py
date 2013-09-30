from circus.commands.base import Command
from circus.exc import ArgumentError


class Restart(Command):
    """\
        Restart the arbiter or a watcher
        ================================

        This command restart all the process in a watcher or all watchers. This
        funtion simply stop a watcher then restart it.

        ZMQ Message
        -----------

        ::

            {
                "command": "restart",
                "properties": {
                    "name": "<name>",
                    "waiting": False
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the watcher.

        If ``waiting`` is False (default), the call will return immediatly
        after calling SIGTERM on each process.

        If ``waiting`` is True, the call will return only when the restart
        process is completly ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl restart [<name>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
    """

    name = "restart"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            return watcher.restart()
        else:
            return arbiter.restart()
