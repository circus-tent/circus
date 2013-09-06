import functools

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
    options = [('async', 'async', False, "Run asynchronously")]

    def message(self, *args, **opts):
        return self.make_message(async=opts.get('async', False))

    def execute(self, arbiter, opts):
        async = opts.get('async', False)
        if async:
            callback = functools.partial(arbiter.stop_watchers,
                                         stop_alive=True,
                                         async=False)

            arbiter.loop.add_callback(callback)
        else:
            arbiter.stop_watchers(stop_alive=True, async=False)
