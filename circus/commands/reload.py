from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Reload(Command):
    """\
        Reload the trainer or a show
        ============================

        This command reload all the fly in a show or all shows. If a
        the option send_hup is set to true in a show then the HUP signal
        will be sent to the fly.A graceful reload follow the following
        process:


        1. Send a SIGQUIT signal to a fly
        2. Wait until graceful timeout
        3. Send a SIGKILL signal to the fly to make sure it is finally
        killed.

        ZMQ Message
        -----------

        ::

            {
                "command": "reload",
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
    name = "reload"
    options = [('', 'terminate', False, "stop immediately")]

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("invalid number of arguments")

        graceful = not opts.get("terminate", False)
        if len(args) == 1:
            return self.make_message(name=args[0], graceful=graceful)
        else:
            return self.make_message(graceful=graceful)

    def execute(self, trainer, props):
        if 'name' in props:
            show = self._get_show(trainer, props['name'])
            show.reload(graceful=props.get('graceful', True))
        else:
            trainer.reload(graceful=props.get('graceful', True))
