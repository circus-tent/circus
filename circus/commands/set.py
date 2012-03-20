from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.py3compat import string_types, integer_types
from circus import util

class Set(Command):
    """\
        Set a show option
        =================

        ZMQ Message
        -----------

        ::

            {
                "command": "set",
                "properties": {
                    "name": "nameofshow",
                    "key1": "val1",
                    ..
                }
            }


        The response return the status "ok". See the command Options for
        a list of key to set.

        Command line
        ------------

        ::

            circusctl set <name> <key1> <value1> <key2> <value2>


    """

    name = "set"
    properties = ['name', 'options']

    def _convert_opt(self, key, val):
        action = 0
        if key == "numflies":
            return int(val)
        elif key == "warmup_delay":
            return float(val)
        elif key == "working_dir":
            return val
        elif key == "uid":
            return val
        elif key == "gid":
            return val
        elif key == "send_hup":
            return util.to_bool(val)
        elif key == "shell":
            return util.to_bool(val)
        elif key == "env":
            return util.parse_env(val)
        elif key == "cmd":
            return  val
        elif key == "times":
            return int(val)
        elif key == "within":
            return float(val)
        elif key == "retry_in":
            return float(val)
        elif key == "max_retry":
            return int(val)
        elif key == "graceful_timeout":
            return float(val)
        raise ArgumentError("unkown key %r" % key)

    def _validate_opt(self, key, val):
        if key not in ('numflies', 'warmup_delay', 'working_dir', 'uid',
                'gid', 'send_hup', 'shell', 'env', 'cmd', 'times',
                'within', 'retry_in', 'max_retry', 'graceful_timeout'):
            raise MessageError('unkown key %r' % key)

        if key in ('numflies', 'times', 'max_retry',):
            if not isinstance(val, int):
                raise MessageError("%r isn't an integer" % key)

        if key in ('warmup_delay', 'within', 'retry_in', 'graceful_timeout',):
            if not isinstance(val, (int, float,)):
                raise MessageError("%r isn't a number" % key)

        if key in ('uid','gid',):
            if not isinstance(val, int) or not isinstance(val, string_types):
                raise MessageError("%r isn't an integer or string" % key)

        if key in ('send_hup', 'shell', ):
            if not isinstance(val, bool):
                raise MessageError("%r isn't a valid boolean" % key)

        if key == "env":
            if not isinstance(val, dict):
                raise MessageError("%r isn't a valid object" % key)

            for k, v in val.items():
                if not isinstance(v, string_types):
                    raise MessageError("%r isn't a string" % k)


    def message(self, *args, **opts):
        if len(args) < 3:
            raise ArgumentError("number of arguments invalid")

        args = list(args)
        show_name = args.pop(0)
        if len(args) % 2 != 0:
            raise ArgumentError("List of key/values is invalid")

        options = {}
        while len(args) > 0:
            kv, args = args[:2], args[2:]
            kvl = kv[0].lower()
            options[kvl] = self._convert_opt(kvl, kv[1])

        return self.make_message(name=show_name, options=options)

    def execute(self, trainer, props):
        show = self._get_show(trainer, props.pop('name'))
        action = 0
        for key, val in props.get('options', {}).items():
            new_action = show.set_opt(key, val)
            if new_action == 1:
                action = 1

        # trigger needed action
        show.do_action(action)

    def validate(self, props):
        super(Set, self).validate(props)
        for key, val in props.get('options').items():
            self._validate_opt(key, val)

