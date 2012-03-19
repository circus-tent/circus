from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.py3compat import string_types, integer_types
from circus import util

class Set(Command):
    """ Set a show option

    Options (IN JSON):

    - numflies: integer, number of flies
    - warmup_delay: integer or number, delay to wait between fly spawning in
      seconds
    - working_dir: string, directory where the fly will be executed
    - uid: string or integer, user ID used to launch the fly
    - gid: string or integer, group ID used to launch the fly
    - send_hup: boolean, if TRU the signal HUP will be used on reload
    - shell: boolean, will run the command in the shell environment if
      true
    - cmd: string, The command line used to launch the fly
    - env: object, define the environnement in which the fly will be
      launch
    - times: integer, number of times we try to relaunch a fly in the within time
      before we stop the show during the retry_in time.
    - within: integer or number, times in seconds in which we test the number
      of fly restart.
    - retry_in: integer or number, times we wait before we retry to launch the fly
      if macium of times have been reach.
    - max_retry: integer, The maximum of retries loops
    - graceful_timeout: integer or number, time we wait before we
      definitely kill a fly when using the graceful option.

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

