from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class NumShows(Command):
    """Get the number of shows"""

    name = "numshows"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("invalid number of arguments")
        return self.make_message()

    def execute(self, trainer, props):
        return {"numshows": trainer.numshows()}
