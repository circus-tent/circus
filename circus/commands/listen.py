from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError

class Listen(Command):
    """\
        Suscribe to a show event
        ========================

        ZMQ
        ---

        At any moment you can suscribe to circus event. Circus provide a
        PUB/SUB feed on which any clients can suscribe. The suscriber
        endpoint URI is set in the circus.ini configuration file.

        Events are pubsub topics:

        Events are pubsub topics:

        - `show.<showname>.reap': when a fly is reaped
        - `show.<showname>.spawn': when a fly is spawned
        - `show.<showname>.kill': when a fly is killed
        - `show.<showname>.updated': when show configuration is updated
        - `show.<showname>.stop': when a show is stopped
        - `show.<showname>.start': when a show is started

        All events messages are in a json.

        Command line
        ------------

        The client has been updated to provide a simple way to listen on the
        events::

            circusctl list [<topic>, ...]

        Example of result:
        ++++++++++++++++++

        ::

            $ circusctl listen tcp://127.0.0.1:5556
            show.refuge.spawn: {u'fly_id': 6, u'fly_pid': 72976, u'time': 1331681080.985104}
            show.refuge.spawn: {u'fly_id': 7, u'fly_pid': 72995, u'time': 1331681086.208542}
            show.refuge.spawn: {u'fly_id': 8, u'fly_pid': 73014, u'time': 1331681091.427005}
    """
    name = "listen"
    msg_type = "sub"

    def message(self, *args, **opts):
        if not args:
            return [""]
        return list(args)

    def execute(self, trainer, args):
        raise MessageError("invalid message. use a pub/sub socket")
