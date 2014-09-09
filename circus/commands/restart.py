import re
import fnmatch
from functools import partial
from circus.commands.base import Command
from circus.exc import ArgumentError, MessageError
from circus.util import TransformableFuture


def execute_watcher_start_stop_restart(arbiter, props, watcher_function_name,
                                       watchers_function, arbiter_function):
    """base function to handle start/stop/restart watcher requests.
    since this is always the same procedure except some function names this
    function handles all watcher start/stop commands
    """
    if 'name' in props:
        name = re.compile(fnmatch.translate(props['name']))
        watchers = [watcher
                    for watcher in arbiter.iter_watchers()
                    if name.match(watcher.name.lower())]
        if not watchers:
            raise MessageError("program %s not found" % props['name'])

        if len(watchers) == 1:
            if props.get('waiting'):
                resp = TransformableFuture()
                func = getattr(watchers[0], watcher_function_name)
                resp.set_upstream_future(func())
                resp.set_transform_function(lambda x: {"info": x})
                return resp
            return getattr(watchers[0], watcher_function_name)()

        def watcher_iter_func(reverse=True):
            return sorted(watchers, key=lambda a: a.priority, reverse=reverse)

        return watchers_function(watcher_iter_func=watcher_iter_func)
    else:
        return arbiter_function()


class Restart(Command):
    """\
        Restart the arbiter or a watcher
        ================================

        This command restart all the process in a watcher or all watchers. This
        funtion simply stop a watcher then restart it.

        ZMQ Message
        -----------

        ::

            {
                "command": "restart",
                "properties": {
                    "name": "<name>",
                    "waiting": False
                }
            }

        The response return the status "ok".

        If the property name is present, then the reload will be applied
        to the watcher.

        If ``waiting`` is False (default), the call will return immediately
        after calling `stop_signal` on each process.

        If ``waiting`` is True, the call will return only when the restart
        process is completely ended. Because of the
        :ref:`graceful_timeout option <graceful_timeout>`, it can take some
        time.


        Command line
        ------------

        ::

            $ circusctl restart [<name>] [--waiting]

        Options
        +++++++

        - <name>: (wildcard) name of the watcher(s)
    """

    name = "restart"
    options = Command.waiting_options

    def message(self, *args, **opts):
        if len(args) > 1:
            raise ArgumentError("Invalid number of arguments")

        if len(args) == 1:
            return self.make_message(name=args[0], **opts)

        return self.make_message(**opts)

    def execute(self, arbiter, props):
        return execute_watcher_start_stop_restart(
            arbiter, props, 'restart', arbiter.restart,
            partial(arbiter.restart, inside_circusd=True))
