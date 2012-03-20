from circus.commands.base import Command
from circus.exc import MessageError

class Quit(Command):
    """\
        Quit the trainer immediately
        ============================

        When the trainer receive this command, the trainer exit.

        ZMQ Message
        -----------

        ::

            {
                "command": "quit",
                "propeties": {
                    "graceful": true
                }
            }

        The response return the status "ok". If the property graceful is
        set to true the flies will be exited gracefully.


        Command line
        ------------

        ::

            circusctl quit [--terminate]

        Options
        +++++++

        - --terminate; quit the node immediately

    """
    name = "quit"
    options = [('', 'terminate', False, "quit immediately")]

    def message(self, *args, **opts):
        graceful = not opts.get("terminate")
        return self.make_message(graceful=graceful)

    def execute(self, trainer, opts):
        trainer.stop(graceful=opts.get('graceful', True))
