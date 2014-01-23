from circus.commands.base import Command
from circus.commands.util import validate_option
from circus.exc import ArgumentError, MessageError


class AddWatcher(Command):
    """\
        Add a watcher
        =============

        This command add a watcher dynamically to a arbiter.

        ZMQ Message
        -----------

        ::

            {
                "command": "add",
                "properties": {
                    "cmd": "/path/to/commandline --option"
                    "name": "nameofwatcher"
                    "args": [],
                    "options": {},
                    "start": false
                }
            }

        A message contains 2 properties:

        - cmd: Full command line to execute in a process
        - args: array, arguments passed to the command (optional)
        - name: name of watcher
        - options: options of a watcher
        - start: start the watcher after the creation

        The response return a status "ok".

        Command line
        ------------

        ::

            $ circusctl add [--start] <name> <cmd>

        Options
        +++++++

        - <name>: name of the watcher to create
        - <cmd>: full command line to execute in a process
        - --start: start the watcher immediately

    """

    name = "add"
    options = [('', 'start', False, "start immediately the watcher")]
    properties = ['name', 'cmd']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("Invalid number of arguments")

        return self.make_message(name=args[0], cmd=" ".join(args[1:]),
                                 start=opts.get('start', False))

    def execute(self, arbiter, props):
        options = props.get('options', {})

        # check for endpoint_owner uid restriction mode
        # it would be better to use some type of SO_PEERCRED lookup on the ipc
        # socket to get the uid of the client process and restrict on that,
        # but there's no good portable pythonic way of doing that right now
        # inside pyzmq or here. So we'll assume that the administrator has
        # set good rights on the ipc socket to help prevent privilege
        # escalation
        if arbiter.endpoint_owner_mode:
            cmd_uid = options.get('uid', None)
            if cmd_uid != arbiter.endpoint_owner:
                raise MessageError("uid does not match endpoint_owner")
        watcher = arbiter.add_watcher(props['name'], props['cmd'],
                                      args=props.get('args'), **options)
        if props.get('start', False):
            return watcher.start()

    def validate(self, props):
        super(AddWatcher, self).validate(props)
        if 'options' in props:
            options = props.get('options')
            if not isinstance(options, dict):
                raise MessageError("'options' property should be an object")

            for key, val in props['options'].items():
                validate_option(key, val)
