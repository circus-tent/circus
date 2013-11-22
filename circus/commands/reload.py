from circus.commands.base import Command
from circus.exc import ArgumentError
from circus.util import TransformableFuture


class Reload(Command):
    """\
        Reload the arbiter or a watcher
        ===============================

        This command reloads all the process in a watcher or all watchers. This
        will happen in one of 3 ways:

        * If graceful is false, a simple restart occurs.
        * If `send_hup` is true for the watcher, a HUP signal is sent to each
          process.
        * Otherwise, the arbiter will attempt to spawn `numprocesses` new
          processes. If the new processes are spawned successfully, the result
          is that all of the old processes are stopped, since by
          default the oldest processes are stopped when the actual number of
          processes for a watcher is greater than `numprocesses`.


        ZMQ Message
        -----------

        ::

            {
                "command": "reload",
                "properties": {
                    "name": '<name>",
                    "graceful": true,
                    "waiting": False
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the processes will be exited gracefully.

        If the property name is present, then the reload will be applied
        to the watcher.


        Command line
        ------------

        ::

            $ circusctl reload [<name>] [--terminate] [--waiting]

        Options
        +++++++

        - <name>: name of the watcher
        - --terminate; quit the node immediately

    """
    name = "reload"
    options = (Command.options + Command.waiting_options +
               [('', 'terminate', False, "stop immediately")])

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        graceful = not opts.get("terminate", False)
        waiting = opts.get("waiting", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful,
                                     waiting=waiting)
        else:
            return self.make_message(graceful=graceful, waiting=waiting)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            if props.get('waiting'):
                resp = TransformableFuture()
                resp.set_upstream_future(watcher.reload(
                    graceful=props.get('graceful', True)))
                resp.set_transform_function(lambda x: {"info": x})
                return resp
            return watcher.reload(graceful=props.get('graceful', True))
        else:
            return arbiter.reload(graceful=props.get('graceful', True))
