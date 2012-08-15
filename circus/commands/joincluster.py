from circus.commands.base import Command
from circus.exc import ArgumentError


class JoinCluster(Command):
    """\
        Provide a node with its name and begin listening to heartbeats from master.
        ===========================================================================

        ZMQ Message
        -----------

        ::

            {
                "command": "join_cluster",
                "properties": {
                    "node_name": "<node_name>",
                    "master_endpoint": <master_endpoint>
                }
            }

        The response return the number of processes in the 'numprocesses`
        property::

            { "status": "ok", "numprocesses": <n>, "time", "timestamp" }

        Command line
        ------------

        ::

            $ circusctl join_cluster <node_name> <master_endpoint>

        Options
        +++++++

        - <node_name>: name of the node.
        - <master_endpoint>: the address of the endpoint of the master.

    """

    name = "joincluster"
    properties = ['node_name', 'master_endpoint']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")
        return self.make_message(node_name=args[0], master_endpoint=args[1])

    def execute(self, arbiter, props):
        arbiter.set_cluster_properties(props['node_name'], props['master_endpoint'])
        return {'node_name': props['node_name']}

    def console_msg(self, msg):
        if msg.get("status") == "ok":
            return "node '" + msg.get('node_name') + "' successfully joined cluster"
        return self.console_error(msg)
