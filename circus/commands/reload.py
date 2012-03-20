from circus.commands.base import Command
from circus.exc import ArgumentError


class Reload(Command):
    """\
        Reload the arbiter or a watcher
        ===============================

        This command reload all the process in a watcher or all watchers. If a
        the option send_hup is set to true in a watcher then the HUP signal
        will be sent to the process.A graceful reload follow the following
        process:


        1. Send a SIGQUIT signal to a process
        2. Wait until graceful timeout
        3. Send a SIGKILL signal to the process to make sure it is finally
           killed.

        ZMQ Message
        -----------

        ::

            {
                "command": "reload",
                "propeties": {
                    "name": '<name>",
                    "graceful": true
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the processes will be exited gracefully.

        If the property name is present, then the reload will be applied
        to the watcher.


        Command line
        ------------

        ::

            $ circusctl reload [<name>] [--terminate]

        Options
        +++++++

        - <name>: name of the watcher
        - --terminate; quit the node immediately

    """
    name = "reload"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        graceful = not opts.get("terminate", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful)
        else:
            return self.make_message(graceful=graceful)

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            watcher.reload(graceful=props.get('graceful', True))
        else:
            arbiter.reload(graceful=props.get('graceful', True))
