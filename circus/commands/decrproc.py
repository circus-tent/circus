from circus.commands.incrproc import IncrProc
from circus.util import TransformableFuture


class DecrProc(IncrProc):
    """\
        Decrement the number of processes in a watcher
        ==============================================

        This comment decrement the number of processes in a watcher
        by <nbprocess>, 1 being the default.

        ZMQ Message
        -----------

        ::

            {
                "command": "decr",
                "propeties": {
                    "name": "<watchername>"
                    "nb": <nbprocess>
                    "waiting": False
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl decr <name> [<nb>] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
        - <nb>: the number of processes to remove.

    """
    name = "decr"
    properties = ['name']

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        if watcher.singleton:
            return {"numprocesses": watcher.numprocesses, "singleton": True}
        else:
            nb = props.get('nb', 1)
            resp = TransformableFuture()
            resp.set_upstream_future(watcher.decr(nb))
            resp.set_transform_function(lambda x: {"numprocesses": x})
            return resp
