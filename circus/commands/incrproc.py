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
                "properties": {
                    "name": "<watchername>",
                    "nb": <nbprocess>
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl incr <name> [<nbprocess>]

        Options
        +++++++

        - <name>: name of the watcher.
        - <nbprocess>: the number of processes to add.

    """

    name = "incr"
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")
        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        if watcher.singleton:
            return {"numprocesses": watcher.numprocesses, "singleton": True}
        else:
            nb = props.get("nb", 1)
            return {"numprocesses": watcher.incr(nb)}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            if "singleton" in msg:
                return ('This watcher is a Singleton - not raising the number '
                        ' of processes')
            else:
                return str(msg.get("numprocesses"))
        return self.console_error(msg)
