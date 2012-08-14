from circus.commands.base import Command
from circus.exc import ArgumentError


class RegisterNode(Command):
    """\
        Register a node name and address with the master
        ================================================

        ZMQ Message
        -----------

        ::

            {
                "command": "register_node",
                "properties": {
                    "node_name": "<node_name>",
                    "node_endpoint": <node_endpoint>
                    "node_stats_endpoint": <node_stats_endpoint>
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl register_node <node_name> <node_endpoint> <node_stats_endpoint>

        Options
        +++++++

        - <node_name>: name of the node.
        - <node_endpoint>: the address of the endpoint of the node.
        - <node_stats_endpoint>: the address of the stats endpoint of the node.

    """

    name = "register_node"
    properties = ['node_name', 'node_endpoint', 'node_stats_endpoint']

    def message(self, *args, **opts):
        if len(args) < 3:
            raise ArgumentError("number of arguments invalid")
        return self.make_message(node_name=args[0], node_endpoint=args[1], node_stats_endpoint=args[2])

    def execute(self, arbiter, props):
        node_name = props['node_name']
        if not node_name in arbiter.nodes:
            arbiter.nodes[node_name] = {'endpoint': props['node_endpoint'], 'stats_endpoint': props['node_stats_endpoint']}
            if hasattr(arbiter.ctrl, 'stats_forwarder'):
                arbiter.ctrl.stats_forwarder.add_connection(props['node_stats_endpoint'])
            success = True
        else:
            success = False
        return {'success': success, 'node_name': node_name}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return "node '" + msg.get('node_name') + "' successfully registered"
        return self.console_error(msg)
