from circus.commands.base import Command
from circus.exc import ArgumentError


class NodeList(Command):
    """\
        Get the list of nodes and each node's address
        ==============================================

        ZMQ Message
        -----------


        To get the list of all the watchers::

            {
                "command": "nodelist",
            }


        The response returns a mapping of node names to node addresses.

        Command line
        ------------

        ::

            $ circusctl nodelist
    """
    name = "nodelist"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("message invalid")

        else:
            return self.make_message()

    def execute(self, arbiter, props):
        nodes_list = {}
        for node in arbiter.nodes:
            nodes_list[node['name']] = node['endpoint']
        return {'nodelist': nodes_list}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            nodelist = msg.get("nodelist")
            return '\n'.join([name + ': ' + nodelist[name] for name in sorted(nodelist)])                
        return self.console_error(msg)
