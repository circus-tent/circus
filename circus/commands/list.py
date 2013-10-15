from circus.commands.base import Command
from circus.exc import ArgumentError

from circus import logger


class List(Command):
    """\
        Get list of watchers or processes in a watcher
        ==============================================

        ZMQ Message
        -----------


        To get the list of all the watchers::

            {
                "command": "list",
            }


        To get the list of active processes in a watcher::

            {
                "command": "list",
                "properties": {
                    "name": "nameofwatcher",
                }
            }


        The response return the list asked. the mapping returned can either be
        'watchers' or 'pids' depending the request.

        Command line
        ------------

        ::

            $ circusctl list [<name>]
    """
    name = "list"

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0])
        else:
            return self.make_message()

    def execute(self, arbiter, props):
        if 'name' in props:
            watcher = self._get_watcher(arbiter, props['name'])
            processes = watcher.get_active_processes()
            status = [(p.pid, p.status) for p in processes]
            logger.debug('here is the status of the processes %s' % status)
            return {"pids":  [p.pid for p in processes]}
        else:
            watchers = sorted(arbiter._watchers_names)
            return {"watchers": [name for name in watchers]}

    def console_msg(self, msg):
        if "pids" in msg:
            return ",".join([str(process_id)
                             for process_id in msg.get('pids')])
        elif 'watchers' in msg:
            return ",".join([watcher for watcher in msg.get('watchers')])
        if 'reason' not in msg:
            msg['reason'] = "Response doesn't contain 'pids' nor 'watchers'."
        return self.console_error(msg)
