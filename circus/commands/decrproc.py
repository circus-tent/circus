from circus.commands.base import Command
from circus.exc import ArgumentError


class DecrProcess(Command):
    """\
        Decrement the number of processes in a watcher
        ==============================================

        This comment decrement the number of processes in a watcher by -1.

        ZMQ Message
        -----------

        ::

            {
                "command": "decr",
                "propeties": {
                    "name": "<watchername>"
                    "nb": <nbprocess>
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl descr <name> [<nbprocess>]

        Options
        +++++++

        - <name>: name of the watcher
        - <nbprocess>: the number of processes to remove.

    """

    name = "decr"
    properties = ['name']

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        nb = props.get('nb', 1)
        return {"numprocesses": watcher.decr(nb)}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numprocesses"))
        return self.console_error(msg)
