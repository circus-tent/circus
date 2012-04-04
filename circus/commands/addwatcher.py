from circus.commands.base import Command
from circus.commands.start import Start
from circus.exc import ArgumentError


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
                }
            }

        A message contains 2 properties:

        - cmd: Full command line to execute in a process
        - name: name of watcher

        The response return a status "ok".

        Command line
        ------------

        ::

            $ circusctl add [--start] <name> <cmd>

        Options
        +++++++

        - <name>: name of the watcher to create
        - <cmd>: ull command line to execute in a process
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
        arbiter.add_watcher(props['name'], props['cmd'])
