from circus.commands.base import Command

class Stats(Command):
    """Get process infos"""

    name = "stats"

    def message(self, *args, **opts):
        if len(args) > 2:
            raise ArgumentError("message invalid")

        if len(args) == 2:
            return "STATS %s %s" % (args[0], args[1])
        elif len(args) == 1:
            return "STATS %s" % args[0]
        else:
            return "STATS"

    def execute(self, trainer, args):
        if len(args) > 2:
            raise MessageError("message invalid")

        if len(args) == 2:
            show = self._get_show(trainer, args[0])
            try:
                return show.fly_info(args[1])
            except KeyError:
                raise MessageError("fly %r not found in %r" % (args[1],
                                    args[0]))

        elif len(args) == 1:
            show = self._get_show(trainer, args[0])
            return "\n".join(show.info())
        else:
            infos = []
            for show in trainer.shows:
                infos.append("%s:\n" % show.name)
                show_info = "\n".join(show.info())
                infos.append("%s\n" % show_info)
            return buffer("".join(infos))
