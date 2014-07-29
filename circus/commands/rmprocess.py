from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class RmProcess(Command):
    """\
        Remove processes in a watcher
        ==============================================

        This comment removes processes in a watcher.

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
        - <pids>: list of pids to remove

    """

    name = "rmprocess"
    properties = ['name', 'pids']
    options = Command.waiting_options

    def message(self, *args, **opts):
        largs = len(args)
        if largs != 2:
            raise ArgumentError("Invalid number of arguments")

        props = {
            'name': args[0],
            'pids': args[1],
        }
        return self.make_message(**props)

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        if watcher.singleton:
            return {"numprocesses": watcher.numprocesses, "singleton": True, 'pids': []}
        else:
            #resp = TransformableFuture()
            #resp.set_upstream_future(watcher.rm_processes(props['pids']))
            #resp.set_transform_function(lambda x: {'resultom':x})
            _r = watcher.rm_processes(props['pids'])
            return _r

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("nr", "ok"))
        return self.console_error(msg)
