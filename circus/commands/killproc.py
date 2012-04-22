from circus.commands.base import Command
from circus.exc import ArgumentError


class KillProcess(Command):
    """\
        Kill a specific process in a watcher
        ====================================

        This command kills a specific process in a watcher.

        ZMQ Message
        -----------

        ::

            {
                "command": "killproc",
                "properties": {
                    "name": "<watchername>",
                    "pid": "<processid>
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl killproc <name> <pid>

        Options
        +++++++

        - <name>: name of the watcher
        - <pid>: pid of the process to kill

    """

    name = "killproc"
    properties = ['name', 'pid']

    def message(self, *args, **opts):

        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0], pid=args[1])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        process = watcher.processes[int(props.get('pid'))]
        watcher.kill_process(process)
        return {"numprocesses": watcher.numprocesses}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numprocesses"))
        return self.console_error(msg)
