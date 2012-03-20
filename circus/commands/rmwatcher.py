from circus.commands.base import Command
from circus.exc import ArgumentError


class RmWatcher(Command):
    """\
        Remove a watcher
        ================

        This command remove a watcher dynamically from the arbiter. The
        watchers can be gracefully stopped.

        ZMQ Message
        -----------

        ::

            {
                "command": "rm",
                "properties": {
                    "name": "nameofwatcher",
                    "graceful": true
                }
            }

        A message contains 2 properties:

        - name: name of watcher
        - graceful: graceful stop

        The response return a status "ok".

        Command line
        ------------

        ::

            $ circusctl rm [--terminate] <name>

        Options
        +++++++

        - <name>: name of the watcher to create
        - --terminate; quit the node immediately

    """

    name = "rm"
    options = [('', 'terminate', False, "stop immediately")]
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1 or len(args) > 1:
            raise ArgumentError("number of arguments invalid")

        graceful = not opts.get("terminate", False)
        return self.make_message(name=args[0], graceful=graceful)

    def execute(self, arbiter, args):
        arbiter.rm_watcher(args['name'])
