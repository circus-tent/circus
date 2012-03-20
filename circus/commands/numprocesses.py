from circus.commands.base import Command
from circus.exc import ArgumentError


class NumProcesses(Command):
    """\
        Get the number of processes
        ===========================

        Get the number of processes in a watcher or in a arbiter

        ZMQ Message
        -----------

        ::

            {
                "command": "numprocesses",
                "propeties": {
                    "name": "<watchername>"
                }

            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        If the property name isn't specified, the sum of all processes
        managed is returned.

        Command line
        ------------

        ::

            $ circusctl numprocesses [<name>]

        Options
        +++++++

        - <name>: name of the watcher

    """
    name = "numprocesses"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            return {
                "numprocesses": len(watcher),
                "watcher_name": props['name']
            }
        else:
            return {"numprocesses": arbiter.numprocesses()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numprocesses"))
        return self.console_error(msg)
