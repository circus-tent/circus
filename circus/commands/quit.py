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
                "async": False
            }

        The response return the status "ok".

        If async is True, the graceful period for process termination
        will be done in the background, and a response will be returned
        immediatly. (defaults: False).


        Command line
        ------------

        ::

            $ circusctl quit

    """
    name = "quit"

    def message(self, *args, **opts):
        async = len(args) > 0 and args[0] or False
        return self.make_message(async=async)

    def execute(self, arbiter, opts):
        async = opts.get('async', False)
        arbiter.stop_watchers(stop_alive=True, async=async)
