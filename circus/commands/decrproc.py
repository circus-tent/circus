from circus.commands.incrproc import IncrProc


class DecrProcess(IncrProc):
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

            $ circusctl descr <name> [<nb>]

        Options
        +++++++

        - <name>: name of the watcher
        - <nb>: the number of processes to remove.

    """
    name = "decr"
    properties = ['name']

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))
        nb = props.get('nb', 1)
        return {"numprocesses": watcher.decr(nb)}
