from circus.commands.base import Command
from circus.exc import ArgumentError


class IncrProc(Command):
    """\
        Increment the number of processes in a watcher
        ==============================================

        This comment increment the number of processes in a watcher by +1.

        ZMQ Message
        -----------

        ::

            {
                "command": "incr",
                "propeties": {
                    "name": "<watchername>"
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl incr <name>

        Options
        +++++++

        - <name>: name of the watcher

    """

    name = "incr"
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")
        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        return {"numprocesses": watcher.incr()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numprocesses"))
        return self.console_error(msg)
