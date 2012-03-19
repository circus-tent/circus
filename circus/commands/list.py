from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class List(Command):
    """ Get list of shows or flies in a show """

    name = "list"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            flies = sorted(show.flies)
            return {"flies": flies}
        else:
            shows = sorted(trainer._shows_names)
            return {"shows": [name for name in shows]}

    def console_msg(self, msg):
        if "flies" in msg:
            return ",".join([str(fly_id) for fly_id in msg.get('flies')])
        elif 'shows' in msg:
            return ",".join([show for show in msg.get('shows')])
        return self.console_error(msg)
