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
                "propeties": {
                    "name": '<name>"
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the watcher.


        Command line
        ------------

        ::

            $ circusctl restart [<name>] [--terminate]

        Options
        +++++++

        - <name>: name of the watcher
        - --terminate; quit the node immediately

    """
    name = "restart"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.restart()
        else:
            arbiter.restart()
