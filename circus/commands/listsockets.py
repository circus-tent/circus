from circus.commands.base import Command
import operator


class ListSockets(Command):
    """\
        Get the list of sockets
        =======================

        ZMQ Message
        -----------


        To get the list of sockets::

            {
                "command": "listsockets",
            }


        The response return a list of json mappings with keys for fd, name,
        host and port.

        Command line
        ------------

        ::

            $ circusctl listsockets
    """
    name = "listsockets"

    def message(self, *args, **opts):
        return self.make_message()

    def execute(self, arbiter, props):
        sockets = [{'fd': socket.fileno(), 'name': socket.name,
                    'host': socket.host, 'port': socket.port,
                    'backlog': socket.backlog}
                   for socket in arbiter.sockets.values()]
        sockets.sort(key=operator.itemgetter('fd'))
        return {"sockets": sockets}

    def console_msg(self, msg):
        if 'sockets' in msg:
            return "\n".join(['%d:socket %r at %s:%d' % (
                s['fd'], s['name'], s['host'], s['port'])
                for s in msg['sockets']])

        return self.console_error(msg)
