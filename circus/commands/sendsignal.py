from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import to_signum


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

        It is also possible to send a signal to all the children of the
        watcher::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>,
                    "children": True
            }

        Lastly, you can send a signal to the process *and* its children, with
        the *recursive* option::

            {
                "command": "signal",
                "property": {
                    "name": <name>,
                    "signum": <signum>,
                    "recursive": True
            }



        Command line
        ------------

        ::

            $ circusctl signal <name> [<pid>] [--children]
                    [--recursive] <signum>

        Options:
        ++++++++

        - <name>: the name of the watcher
        - <pid>: integer, the process id.
        - <signum>: the signal number (or name) to send.
        - <childpid>: the pid of a child, if any
        - <children>: boolean, send the signal to all the children
        - <recursive>: boolean, send the signal to the process and its children

    """

    name = "signal"
    options = [('', 'children', False, "Only signal children of the process"),
               ('', 'recursive', False, "Signal parent and children")]
    properties = ['name', 'signum']

    def message(self, *args, **opts):
        largs = len(args)
        if largs < 2 or largs > 3:
            raise ArgumentError("Invalid number of arguments")

        props = {
            'name': args[0],
            'children': opts.get("children", False),
            'recursive': opts.get("recursive", False),
            'signum': args[-1],
        }
        if len(args) == 3:
            props['pid'] = int(args[1])
        return self.make_message(**props)

    def execute(self, arbiter, props):
        name = props.get('name')
        watcher = self._get_watcher(arbiter, name)
        signum = props.get('signum')
        pids = [props['pid']] if 'pid' in props else watcher.get_active_pids()
        childpid = props.get('childpid', None)
        children = props.get('children', False)
        recursive = props.get('recursive', False)

        for pid in pids:
            if childpid:
                watcher.send_signal_child(pid, childpid, signum)
            elif children:
                watcher.send_signal_children(pid, signum)
            else:
                # send to the given pid
                watcher.send_signal(pid, signum)

                if recursive:
                    # also send to the children
                    watcher.send_signal_children(pid, signum, recursive=True)

    def validate(self, props):
        super(Signal, self).validate(props)

        if 'childpid' in props and 'pid' not in props:
            raise ArgumentError('cannot specify childpid without pid')

        try:
            props['signum'] = to_signum(props['signum'])
        except ValueError:
            raise MessageError('signal invalid')
