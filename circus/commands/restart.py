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
                    "async": True
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the watcher.

        If the async flag is set to False, everything will be done
        synchronously in circusd and it will be blocked while doing it.

        If set to True (the default), the process killing will be done
        asynchronously and the command will return before it's over.

        Notice that async is only applied when you restart a specific
        watcher, not the whole arbiter - in that case the call is blocking.

        Command line
        ------------

        ::

            $ circusctl restart [<name>] [async] [--terminate]

        Options
        +++++++

        - <name>: name of the watcher
        - --async: asynchronous process
        - --terminate; quit the node immediately
    """
    name = "restart"
    async = True

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        async = props.get('async')
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.restart(async=async)
        else:
            if async:
                arbiter.loop.add_callback(arbiter.restart)
            else:
                arbiter.restart()
