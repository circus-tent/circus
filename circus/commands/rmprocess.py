from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class RmProcess(Command):
    """\
        Remove processes in a watcher
        ==============================================

        ZMQ Message
        -----------

        ::

            {
                "command": "rmprocess",
                "properties": {
                    "name": "<watchername>",
                    "pids": <pids>
                }
            }

        The response return the number of removed processes in the 'nr`
        property::

            { "status": "ok", "nr": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl rmprocess <name> <pids>

        Options
        +++++++

        - <name>: name of the watcher.
        - <pids>: commma separated list of pids to remove

    """

    name = "rmprocess"
    properties = ['name', 'pids']

    def message(self, *args, **opts):
        if len(args) != 2:
            raise ArgumentError("Invalid number of arguments")

        if not args[1]:
            raise ArgumentError("Invalid pids argument")

        pids = args[1].split(",")
        try:
            pids = [int(pid) for pid in pids]
        except ValueError:
            raise ArgumentError("Process ID must be an integer")

        props = {
            'name': args[0],
            'pids': pids
        }
        return self.make_message(**props)

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        _r = watcher.rm_processes(props['pids'])
        return _r
