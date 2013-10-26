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
                "waiting": False
            }

        The response return the status "ok".

        If ``waiting`` is False (default), the call will return immediately
        after calling ``stop_signal`` on each process.

        If ``waiting`` is True, the call will return only when the stop process
        is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl quit [--waiting]

    """
    name = "quit"
    options = Command.waiting_options

    def message(self, *args, **opts):
        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return arbiter.stop()
