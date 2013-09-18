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

        If ``waiting`` is False (default), the call will return immediatly
        after calling SIGTERM on each process.

        If ``waiting`` is True, the call will return only when the stop process
        is completly ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl quit [--waiting]

    """
    name = "quit"
    callback = True
    options = Command.waiting_options

    def message(self, *args, **opts):
        return self.make_message(**opts)

    def execute_with_cb(self, arbiter, props, callback):
        arbiter.stop(callback=callback)
