from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import to_signum
from tornado import gen


class Kill(Command):
    """\
        Kill a specific process
        =======================

        This command allows you to terminate a process in a watcher. If a
        process does not exit within graceful_timeout it will be terminated
        with a SIGKILL.

        ZMQ Message
        -----------

        To kill all the processes of a watcher::

            {
                "command": "kill",
                "property": {
                    "name": <name>,
                    "signum": <signum>,
                    "graceful_timeout": <graceful_timeout>
                }
            }

        To send a signal to a specific process::

            {
                "command": "kill",
                "property": {
                    "name": <name>,
                    "pid": <processid>,
                    "signum": <signum>,
                    "graceful_timeout": <graceful_timeout>
                }
            }


        Command line
        ------------

        ::

            $ circusctl kill <name> [<pid>] [<signum>] [<graceful_timeout>]

        Options:
        ++++++++

        - <name>: the name of the watcher
        - <pid>: integer, the process id
        - <signum>: overrides the watcher's stop_signal (number or name)
        - <graceful_timeout>: overrides the watcher's graceful_timeout

    """

    name = "kill"
    properties = ['name']

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 1 or largs > 4:
            raise ArgumentError("Invalid number of arguments")

        props = {
            'name': args[0],
        }
        if len(args) >= 2:
            props['pid'] = args[1]
        if len(args) >= 3:
            props['signum'] = args[2]
        if len(args) >= 4:
            props['graceful_timeout'] = args[3]
        return self.make_message(**props)

    @gen.coroutine
    def execute(self, arbiter, props):
        name = props.get('name')
        pid = props.get('pid')
        signum = props.get('signum')
        graceful_timeout = props.get('graceful_timeout')

        watcher = self._get_watcher(arbiter, name)
        processes = watcher.get_active_processes()
        if pid:
            processes = [p for p in processes if p.pid == pid]

        if processes:
            yield [watcher.kill_process(p,
                                        stop_signal=signum,
                                        graceful_timeout=graceful_timeout)
                   for p in processes]

    def validate(self, props):
        super(Kill, self).validate(props)

        if 'pid' in props:
            props['pid'] = int(props['pid'])
        if 'graceful_timeout' in props:
            props['graceful_timeout'] = float(props['graceful_timeout'])

        try:
            if 'signum' in props:
                props['signum'] = to_signum(props['signum'])
        except ValueError:
            raise MessageError('signal invalid')
