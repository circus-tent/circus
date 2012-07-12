import signal

from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.py3compat import string_types


class Signal(Command):
    """\
        Send a signal
        =============

        This command allows you to send a signal to all processes in a watcher,
        a specific process in a watcher or its children.

        ZMQ Message
        -----------

        To send a signal to all the processes for a watcher::

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
                    "pid": <processid>,
                    "signum": <signum>
            }

        An optional property "children" can be used to send the signal
        to all the children rather than the process itself::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "pid": <processid>,
                    "signum": <signum>,
                    "children": True
            }

        To send a signal to a process child::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "pid": <processid>,
                    "signum": <signum>,
                    "child_pid": <childpid>,
            }

        It is also possible to send a signal to all the processes of the
        watcher and its childs::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>,
                    "children": True
            }


        Command line
        ------------

        ::

            $ circusctl signal <name> [<process>] [<pid>] [--children] <signum>

        Options:
        ++++++++

        - <name>: the name of the watcher
        - <pid>: integer, the process id.
        - <signum>: the signal number to send.
        - <childpid>: the pid of a child, if any
        - <children>: boolean, send the signal to all the children

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
        name = props.get('name')
        watcher = self._get_watcher(arbiter, name)
        signum = props.get('signum')
        pid = props.get('pid', None)
        childpid = props.get('childpid', None)
        children = props.get('children', False)

        if pid:
            if childpid:
                watcher.send_signal_child(pid, childpid, signum)
            elif children:
                watcher.send_signal_children(pid, signum)
            else:
                # send to the given pid
                watcher.send_signal(pid, signum)
        else:
            # send to all the pids for this watcher
            watcher.send_signal_processes(signum)

    def validate(self, props):
        super(Signal, self).validate(props)

        signum = props.get('signum')
        if 'statspid' in props and not 'pid' in props:
            raise ArgumentError('cannot specify childpid without pid')
        if 'children' in props and not 'pid' in props:
            raise ArgumentError('cannot specify children without pid')

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
