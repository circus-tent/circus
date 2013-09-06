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

            $ circusctl quit --async

    """
    name = "quit"
    async = False

    def message(self, *args, **opts):
        return self.make_message(**opts)

    def execute(self, arbiter, opts):
        arbiter.stop_watchers(stop_alive=True, async=False)
