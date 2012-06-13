from circus.commands.base import Command


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


        The response return the list asked.

        Command line
        ------------

        ::

            $ circusctl listsockets
    """
    name = "listsockets"

    def message(self, *args, **opts):
        return self.make_message()

    def execute(self, arbiter, props):
        sockets = [str(socket) for socket in arbiter.sockets.values()]
        sockets.sort()
        return {"sockets": sockets}

    def console_msg(self, msg):
        if 'sockets' in msg:
            return "\n".join(msg['sockets'])

        return self.console_error(msg)
