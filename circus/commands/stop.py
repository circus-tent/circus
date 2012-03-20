from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Stop(Command):
    """\
        Stop the trainer or a show
        ============================

        This command stop all the fly in a show or all shows. The shows
        can be stopped gracefully.

        ZMQ Message
        -----------

        ::

            {
                "command": "stop",
                "propeties": {
                    "name": '<name>",
                    "graceful": true
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the flies will be exited gracefully.

        If the property name is present, then the reload will be applied
        to the show.


        Command line
        ------------

        ::

            circusctl reload [<name>] [--terminate]

        Options
        +++++++

        - <name>: name of the show
        - --terminate; quit the node immediately

    """

    name = "stop"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        graceful = not opts.get("terminate", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful)
            msg = "STOP %s" % args[0]
        else:
            return self.make_message(graceful=graceful)

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            show.stop(graceful=props.get('graceful', True))
        else:
            trainer.stop_shows(graceful=props.get('graceful', True))
