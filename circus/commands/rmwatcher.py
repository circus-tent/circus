from circus.commands.base import Command
from circus.exc import ArgumentError


class RmWatcher(Command):
    """\
        Remove a watcher
        ================

        This command removes a watcher dynamically from the arbiter. The
        watchers are gracefully stopped by default.

        ZMQ Message
        -----------

        ::

            {
                "command": "rm",
                "properties": {
                    "name": "<nameofwatcher>",
                    "nostop": False,
                    "waiting": False
                }
            }

        The response return a status "ok".

        If ``nostop`` is True (default: False), the processes for the watcher
        will not be stopped - instead the watcher will just be forgotten by
        circus and the watcher processes will be responsible for stopping
        themselves. If ``nostop`` is not specified or is False, then the
        watcher processes will be stopped gracefully.

        If ``waiting`` is False (default), the call will return immediately
        after starting to remove and stop the corresponding watcher.

        If ``waiting`` is True, the call will return only when the remove and
        stop process is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl rm <name> [--waiting] [--nostop]

        Options
        +++++++

        - <name>: name of the watcher to remove
        - nostop: do not stop the watcher processes, just remove the watcher

    """

    name = "rm"
    properties = ['name']
    options = Command.waiting_options + \
        [('nostop', 'nostop', False, 'Do not stop watcher processes')]

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        return self.make_message(name=args[0])

    def execute(self, arbiter, props):
        self._get_watcher(arbiter, props['name'])
        return arbiter.rm_watcher(props['name'], props.get('nostop', False))
