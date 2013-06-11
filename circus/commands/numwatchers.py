from circus.commands.base import Command
from circus.exc import ArgumentError


class NumWatchers(Command):
    """\
        Get the number of watchers
        ==========================

        Get the number of watchers in a arbiter

        ZMQ Message
        -----------

        ::

            {
                "command": "numwatchers",
            }

        The response return the number of watchers in the 'numwatchers`
        property::

            { "status": "ok", "numwatchers": <n>, "time", "timestamp" }


        Command line
        ------------

        ::

            $ circusctl numwatchers

    """
    name = "numwatchers"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("Invalid number of arguments")
        return self.make_message()

    def execute(self, arbiter, props):
        return {"numwatchers": arbiter.numwatchers()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numwatchers"))
        return self.console_error(msg)
