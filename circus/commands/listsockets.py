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

        def _get_info(socket):
            sock = {'fd': socket.fileno(),
                    'name': socket.name,
                    'backlog': socket.backlog}

            if socket.host is not None:
                sock['host'] = socket.host
                sock['port'] = socket.port
            else:
                sock['path'] = socket.path

            return sock

        sockets = [_get_info(socket) for socket in arbiter.sockets.values()]
        sockets.sort(key=operator.itemgetter('fd'))
        return {"sockets": sockets}

    def console_msg(self, msg):
        if 'sockets' in msg:
            sockets = []
            for sock in msg['sockets']:
                d = "%(fd)d:socket '%(name)s' "
                if 'path' in sock:
                    d = (d + 'at %(path)s') % sock
                else:
                    d = (d + 'at %(host)s:%(port)d') % sock

                sockets.append(d)

            return "\n".join(sockets)

        return self.console_error(msg)
