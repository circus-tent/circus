from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import convert_opt

class Options(Command):
    """\
        Get the value of a show option
        ==============================

        This command return the shows options values asked.

        ZMQ Message
        -----------

        ::

            {
                "command": "options",
                "properties": {
                    "name": "nameofshow",
                    "key1": "val1",
                    ..
                }
            }

        A message contains 2 properties:

        - keys: list, The option keys for which you want to get the values
        - name: name of show

        The response return an object with a property "options"
        containing the list of key/value returned by circus.

        eg::

            {
                "status": "ok",
                "options": {
                    "within": 1,
                    "times": 2,
                    ...
                },
                time': 1332202594.754644
            }



        Command line
        ------------

        circusctl options <name>


        Options
        -------

        - <name>: name of the show

        Options Keys are:

        - numflies: integer, number of flies
        - warmup_delay: integer or number, delay to wait between fly
          spawning in seconds
        - working_dir: string, directory where the fly will be executed
        - uid: string or integer, user ID used to launch the fly
        - gid: string or integer, group ID used to launch the fly
        - send_hup: boolean, if TRU the signal HUP will be used on reload
        - shell: boolean, will run the command in the shell environment if
          true
        - cmd: string, The command line used to launch the fly
        - env: object, define the environnement in which the fly will be
          launch
        - times: integer, number of times we try to relaunch a fly in
          the within time before we stop the show during the retry_in time.
        - within: integer or number, times in seconds in which we test
          the number of fly restart.
        - retry_in: integer or number, times we wait before we retry to
          launch the fly if macium of times have been reach.
        - max_retry: integer, The maximum of retries loops
        - graceful_timeout: integer or number, time we wait before we
          definitely kill a fly when using the graceful option.

    """

    name = "options"
    properties = ['name']

    def message(self, *args, **opts):

        if len(args) < 1:
            raise ArgumentError("number of arguments invalid")

        return self.make_message(name=args[0])

    def execute(self, trainer, props):
        show = self._get_show(trainer, props['name'])
        return {"options": dict(show.options())}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            ret = []
            for k, v in msg.get('options', {}).items():
                ret.append("%s: %s" % (k, convert_opt(k, v)))
            return "\n".join(ret)
        return self.console_msg(self, msg)
