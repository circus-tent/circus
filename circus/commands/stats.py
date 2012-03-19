from circus.commands.base import Command

class Stats(Command):
    """Get process infos"""

    name = "stats"

    def message(self, *args, **opts):
        if len(args) > 2:
            raise ArgumentError("message invalid")

        if len(args) == 2:
            return self.make_message(name=args[0], fly=int(args[1]))
        elif len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            if 'fly' in props:
                try:
                    return show.fly_info(props['fly'])
                except KeyError:
                    raise MessageError("fly %r not found in %r" % (props['fly'],
                        props['name']))
            else:
                return {"name": props['name'], "info": show.info()}
        else:
            infos = {}
            for show in trainer.shows:
                infos[show.name] = show.info()
            return {"infos": infos}
