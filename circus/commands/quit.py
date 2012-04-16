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
                "command": "quit"
            }

        The response return the status "ok".


        Command line
        ------------

        ::

            $ circusctl quit

    """
    name = "quit"

    def message(self, *args, **opts):
        return self.make_message()

    def execute(self, arbiter, opts):
        arbiter.stop_watchers(stop_alive=True)
