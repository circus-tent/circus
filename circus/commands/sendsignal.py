import signal

from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.py3compat import string_types


class Signal(Command):
    """\
        Send a signal
        =============

        This command allows you to send the signal to all processes in a
        watcher, a specific process in a watcher or its children

        ZMQ Message
        -----------


        To get the list of all process in the watcher::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>
            }

        To send a signal to a process::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "process": <processid>,
                    "signum": <signum>
            }

        An optionnal property "children" can be used to send the signal
        to all the children rather than the process itself.

        To send a signal to a process child:

        To get the list of processes in a watcher::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "process": <processid>,
                    "signum": <signum>,
                    "pid": <pid>
            }


        The response return the status "ok".

        Command line
        ------------

        ::

            $ circusctl signal <name> [<process>] [<pid>] [--children] <signum>

        Options:
        ++++++++

        - <name>: the name of the watcher
        - <process>: the process id. You can get them using the command list
        - <pid>: integer, the process id.
        - <signum> : the signal number to send.

        Allowed signals are:

            - 3:    QUIT
            - 15:   TERM
            - 9:    KILL
            - 1:    HUP
            - 21:   TTIN
            - 22:   TTOU
            - 30:   USR1
            - 31:   USR2


    """

    name = "signal"
    options = [('', 'children', True, "Only signal children of the process")]
    properties = ['name', 'signum']

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 2 or largs > 4:
            raise ArgumentError("number of arguments invalid")

        if len(args) == 4:
            signum = self._get_signal(args[3])
            return self.make_message(name=args[0], process=args[1],
                    pid=args[2], signum=signum)
        elif len(args) == 3:
            signum = self._get_signal(args[2])
            children = opts.get("children", False)
            return self.make_message(name=args[0], process=args[1],
                    signum=signum, children=children)
        else:
            signum = self._get_signal(args[1])
            return self.make_message(name=args[0], signum=signum)

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props['name'])
        signum = props.get('signum')

        if 'pid' in props:
            watcher.send_signal_child(props[1], props[2], signum)
        elif 'process' in props:
            process = props.get('process')
            if props.get('children', False):
                watcher.send_signal_children(process, signum)
            else:
                watcher.send_signal(process, signum)
        else:
            watcher.send_signal_processes(signum)

    def validate(self, props):
        super(Signal, self).validate(props)
        if 'pid' in props and not 'process' in props:
            raise MessageError('process ID is missing')

        if props.get('children', False) and not 'process':
            raise MessageError('process ID is missing')

        signum = props.get('signum')

        if isinstance(signum, int):
            if signum not in (signal.SIGQUIT, signal.SIGHUP, signal.SIGKILL,
                    signal.SIGTERM, signal.SIGTTIN, signal.SIGTTOU,
                    signal.SIGUSR1, signal.SIGUSR2):
                raise MessageError('signal invalid')
        elif isinstance(signum, string_types):
            if signum.lower() in ('quit', 'hup', 'kill', 'term', 'ttin',
                'ttou', 'usr1', 'usr2'):
                props['signum'] = getattr(signal, "SIG%s" % signum.upper())
            else:
                raise MessageError('signal invalid')

        else:
            raise MessageError('signal invalid')
