from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import convert_opt


class Get(Command):
    """\
        Get the value of a watcher option
        =================================

        This command return the watchers options values asked.

        ZMQ Message
        -----------

        ::

            {
                "command": "get",
                "properties": {
                    "keys": ["key1, "key2"]
                    "name": "nameofwatcher"
                }
            }

        A response contains 2 properties:

        - keys: list, The option keys for which you want to get the values
        - name: name of watcher

        The response return an object with a property "options"
        containing the list of key/value returned by circus.

        eg::

            {
                "status": "ok",
                "options": {
                    "within": 1,
                    "times": 2
                },
                time': 1332202594.754644
            }

        See Optios for for a description of options enabled?


        Command line
        ------------

        ::

            $ circusctl get <name> <key> <value> <key1> <value1>

    """

    name = "get"
    properties = ['name', 'keys']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0], keys=args[1:])

    def execute(self, arbiter, props):
        watcher = self._get_watcher(arbiter, props.get('name'))

        # get options values. It return an error if one of the asked
        # options isn't found
        options = {}
        for name in props.get('keys', []):
            if name in watcher.optnames:
                options[name] = getattr(watcher, name)
            else:
                raise MessageError("%r option not found" % name)

        return {"options": options}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            ret = []
            for k, v in msg.get('options', {}).items():
                ret.append("%s: %s" % (k, convert_opt(k, v)))
            return "\n".join(ret)
        return self.console_msg(self, msg)
