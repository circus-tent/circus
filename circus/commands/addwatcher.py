from circus.commands.base import Command
from circus.commands.start import Start
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
            raise ArgumentError("number of arguments invalid")

        msg = self.make_message(name=args[0], cmd=" ".join(args[1:]))
        if opts.get("start", False):
            return [{'cmd': self,
                     'msg': msg},
                    {'cmd': Start(),
                     'msg': self.make_message(command="start", name=args[0])}]
        return msg

    def execute(self, arbiter, props):
        options = props.get('options', {})
        watcher = arbiter.add_watcher(props['name'], props['cmd'],
                                      args=props.get('args'), **options)
        if props.get('start', False):
            watcher.start()

    def validate(self, props):
        super(AddWatcher, self).validate(props)
        if 'options' in props:
            options = props.get('options')
            if not isinstance(options, dict):
                raise MessageError("'options' property shoudl be an object")

            for key, val in props['options'].items():
                validate_option(key, val)
