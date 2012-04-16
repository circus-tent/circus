from circus.commands.base import Command
from circus.exc import ArgumentError


class RmWatcher(Command):
    """\
        Remove a watcher
        ================

        This command remove a watcher dynamically from the arbiter. The
        watchers are gracefully stopped.

        ZMQ Message
        -----------

        ::

            {
                "command": "rm",
                "properties": {
                    "name": "nameofwatcher",
                }
            }

        A message contains 1 property:

        - name: name of watcher

        The response return a status "ok".

        Command line
        ------------

        ::

            $ circusctl rm <name>

        Options
        +++++++

        - <name>: name of the watcher to create

    """

    name = "rm"
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0])

    def execute(self, arbiter, args):
        arbiter.rm_watcher(args['name'])
