import signal

from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Signal(Command):
    """Send a signal """

    name = "signal"
    options = [('', 'children', True, "Only signal children of the fly")]
    properties = ['name', 'signum']

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 2 or largs > 4:
            raise ArgumentError("number of arguments invalid")

        if len(args) == 4:
            signum = self._get_signal(args[3])
            return self.make_message(name=args[0], fly=args[1],
                    pid=args[2], signum=signum)
        elif len(args) == 3:
            signum = self._get_signal(args[2])
            children = opts.get("children", False)
            return self.make_message(name=args[0], fly=args[1],
                    signum=signum, children=children)
        else:
            signum = self._get_signal(args[1])
            return self.make_message(name=args[0], signum=signum)

    def execute(self, trainer, props):
        show = self._get_show(trainer, props['name'])
        signum = props.get('signum')

        if 'pid' in props:
            show.send_signal_child(args[1], args[2], signum)
        elif 'fly' in props:
            fly = props.get('fly')
            if props.get('children', False):
                show.send_signal_children(fly, signum)
            else:
                show.send_signal(fly, signum)
        else:
            show.send_signal_flies(signum)

    def validate(self, props):
        super(Signal, self).validate(props)
        if 'pid' in props and not 'fly' in props:
            raise MessageError('fly ID is missing')

        if props.get('children', False) and not 'fly':
            raise MessageError('fly ID is missing')

        signum = props.get('signum')
        if signum not in (signal.SIGQUIT, signal.SIGHUP, signal.SIGKILL,
                signal.SIGTERM, signal.SIGTTIN, signal.SIGTTOU):
            raise MessageError('signal invalid')



