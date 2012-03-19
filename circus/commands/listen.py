from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Listen(Command):
    """Suscribe to a show event"""

    name = "listen"
    msg_type = "sub"

    def message(self, *args, **opts):
        if not args:
            return [""]
        return list(args)

    def execute(self, trainer, args):
        raise MessageError("invalid message. use a pub/sub socket")
