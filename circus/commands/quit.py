from circus.commands.base import Command


class Quit(Command):
    """\
        Quit the arbiter immediately
        ============================

        When the arbiter receive this command, the arbiter exit.

        ZMQ Message
        -----------

        ::

            {
                "command": "quit",
                "propeties": {
                    "graceful": true
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the flies will be exited gracefully.


        Command line
        ------------

        ::

            $ circusctl quit [--terminate]

        Options
        +++++++

        - --terminate; quit the node immediately

    """
    name = "quit"
    options = [('', 'terminate', False, "quit immediately")]

    def message(self, *args, **opts):
        graceful = not opts.get("terminate")
        return self.make_message(graceful=graceful)

    def execute(self, arbiter, opts):
        arbiter.stop_watchers(graceful=opts.get('graceful', True),
                               stop_alive=True)
