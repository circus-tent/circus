from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class IncrShow(Command):
    """\
        Increment the number of flies in a show
        =======================================

        This comment increment the number of flies in a show by +1.

        ZMQ Message
        -----------

        ::

            {
                "command": "incr",
                "propeties": {
                    "name": "<showname>"
                }
            }

        The message return the number of flies in the 'numberflies`
        property::

            { "status": "ok", "numflies": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            circusctl incr <name>

        Options
        +++++++

        - <name>: name of the show

    """

    name = "incr"
    properties = ['name']

    def message(self, *args, **opts):
        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")
        return self.make_message(name=args[0])

    def execute(self, trainer, props):
        show = self._get_show(trainer, props.get('name'))
        return {"numflies": show.incr()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numflies"))
        return self.console_error(msg)
