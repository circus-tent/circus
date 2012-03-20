from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class NumFlies(Command):
    """\
        Get the number of flies
        =======================

        Get the number of flies in a show or in a trainer

        ZMQ Message
        -----------

        ::

            {
                "command": "numflies",
                "propeties": {
                    "name": "<showname>"
                }

            }

        The response return the number of flies in the 'numflies`
        property::

            { "status": "ok", "numflies": <n>, "time", "timestamp" }

        If the property name isn't specified, the sum of all flies
        managed is returned.

        Command line
        ------------

        ::

            circusctl numflies [<name>]

        Options
        +++++++

        - <name>: name of the show

    """
    name = "numflies"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("message invalid")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            return {
                "numflies": show.numflies,
                "show_name": props['name']
            }
        else:
            return {"numflies": trainer.numflies()}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return str(msg.get("numflies"))
        return self.console_error(msg)
