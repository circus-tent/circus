from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class IncrProc(Command):
    """\
        Increment the number of processes in a watcher
        ==============================================

        This comment increment the number of processes in a watcher
        by <nbprocess>, 1 being the default

        ZMQ Message
        -----------

        ::

            {
                "command": "incr",
                "properties": {
                    "name": "<watchername>",
                    "nb": <nbprocess>,
                    "waiting": False
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl incr <name> [<nb>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher.
        - <nb>: the number of processes to add.

    """

    name = "incr"
    properties = ['name']
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) < 1:
            raise ArgumentError("Invalid number of arguments")
        options = {'name': args[0]}
        if len(args) > 1:
            options['nb'] = int(args[1])
        options.update(opts)
        return self.make_message(**options)

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        if watcher.singleton:
            return {"numprocesses": watcher.numprocesses, "singleton": True}
        else:
            nb = props.get("nb", 1)
            resp = TransformableFuture()
            resp.set_upstream_future(watcher.incr(nb))
            resp.set_transform_function(lambda x: {"numprocesses": x})
            return resp

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            if "singleton" in msg:
                return ('This watcher is a Singleton - not changing the number'
                        ' of processes')
            else:
                return str(msg.get("numprocesses", "ok"))
        return self.console_error(msg)
