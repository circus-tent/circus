from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import convert_opt


class Get(Command):
    """\
        Get the value of specific watcher options
        =========================================

        This command can be used to query the current value of one or
        more watcher options.

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

        A request message contains two properties:

        - keys: list, The option keys for which you want to get the values
        - name: name of watcher

        The response object has a property ``options`` which is a
        dictionary of option names and values.

        eg::

            {
                "status": "ok",
                "options": {
                    "graceful_timeout": 300,
                    "send_hup": True,
                },
                time': 1332202594.754644
            }


        Command line
        ------------

        ::

            $ circusctl get <name> <key1> <key2>

    """

    name = "get"
    properties = ['name', 'keys']

    def message(self, *args, **opts):
        if len(args) < 2:
            raise ArgumentError("Invalid number of arguments")

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
        return self.console_error(msg)
