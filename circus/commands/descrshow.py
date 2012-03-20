from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError


class DecrShow(Command):
    """\
        Decrement the number of flies in a show
        =======================================

        This comment decrement the number of flies in a show by -1.

        ZMQ Message
        -----------

        ::

            {
                "command": "decr",
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

            circusctl descr <name>

        Options
        +++++++

        - <name>: name of the show

    """

    name = "decr"
    properties = ['name']

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0])

    def execute(self, trainer, props):
        show = self._get_show(trainer, props.get('name'))
        return {"numflies": show.decr()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numflies"))
        return self.console_error(msg)
