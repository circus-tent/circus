from circus.commands.base import Command
from circus.exc import ArgumentError


class ListPids(Command):
    """\
        Get list of pids in a watcher
        =============================

        ZMQ Message
        -----------


        To get the list of pid in a watcher::

            {
                "command": "listpids",
                "properties": {
                    "name": "nameofwatcher",
                }
            }


        The response return the list asked.

        Command line
        ------------

        ::

            $ circusctl listpids <name>
    """
    name = "listpids"

    def message(self, *args, **opts):
        if len(args) != 1:
            raise ArgumentError("invalid number of arguments")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props['name'])
        pids = [process.pid for process in watcher.processes.values()]
        pids.sort()
        return {"pids": pids}

    def console_msg(self, msg):
        if 'pids' in msg:
            return ",".join([str(pid) for pid in msg.get('pids')])
        return self.console_error(msg)
