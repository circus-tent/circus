from circus.commands.base import Command
from circus.exc import ArgumentError


class List(Command):
    """\
        Get list of watchers or processes in a watcher
        ==============================================

        ZMQ Message
        -----------


        To get the list of all the watchers::

            {
                "command": "list",
            }


        To get the list of processes in a watcher::

            {
                "command": "list",
                "properties": {
                    "name": "nameofwatcher",
                }
            }


        The response return the list asked. Flies returned are process ID
        that can be used in others commands.

        Command line
        ------------

        ::

            $ circusctl list [<name>]
    """
    name = "list"

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
            processes = sorted(watcher.processes)
            return {"processes": processes}
        else:
            watchers = sorted(arbiter._watchers_names)
            return {"watchers": [name for name in watchers]}

    def console_msg(self, msg):
        if "processes" in msg:
            return ",".join([str(process_id)
                             for process_id in msg.get('processes')])
        elif 'watchers' in msg:
            return ",".join([watcher for watcher in msg.get('watchers')])
        return self.console_error(msg)
