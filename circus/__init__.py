import logging
import os
import warnings


version_info = (0, 16, 1)
__version__ = ".".join(map(str, version_info))

# This config call is done to avoid any
#     "no handlers could be found for logger"
# However, the real configuration has to be done later
logging.basicConfig()
logger = logging.getLogger('circus')


class ArbiterHandler(object):
    def __call__(self, watchers, controller=None,
                 pubsub_endpoint=None,
                 statsd=False,
                 stats_endpoint=None,
                 statsd_close_outputs=False,
                 multicast_endpoint=None,
                 env=None, name=None, context=None,
                 background=False, stream_backend="thread", httpd=False,
                 plugins=None, debug=False, proc_name="circusd",
                 loop=None, check_delay=1.0, **kw):
        """Creates a Arbiter and a single watcher in it.

        Options:

          - **watchers** -- a list of watchers. A watcher in that case is a
                            dict containing:
            - **name** -- the name of the watcher (default: None)
            - **cmd** -- the command line used to run the Watcher.
            - **args** -- the args for the command (list or string).
            - **executable** -- When executable is given, the first item in
              the args sequence obtained from **cmd** is still treated by most
              programs as the command name, which can then be different from
              the actual executable name. It becomes the display name for the
              executing program in utilities such as **ps**.

            - **numprocesses** -- the number of processes to spawn
              (default: 1).
            - **warmup_delay** -- the delay in seconds between two spawns
              (default: 0)
            - **shell** -- if True, the processes are run in the shell
              (default: False)
            - **working_dir** - the working dir for the processes
              (default: None)
            - **uid** -- the user id used to run the processes (default: None)
            - **gid** -- the group id used to run the processes (default: None)
            - **env** -- the environment passed to the processes
              (default: None)
            - **send_hup**: if True, a process reload will be done by sending
              the SIGHUP signal. (default: False)
            - **stdout_stream**: a mapping containing the options for
              configuring
              the stdout stream. Default to None. When provided, may contain:

                - **class**: the fully qualified name of the class to use for
                             streaming. Defaults to circus.stream.FileStream
                - any other key will be passed the class constructor.
            - **stderr_stream**: a mapping containing the options for
              configuring the stderr stream. Default to None. When provided,
              may contain:

                - **class**: the fully qualified name of the class to use for
                  streaming. Defaults to circus.stream.FileStream
                - any other key will be passed the class constructor.
            - **max_retry**: the number of times we attempt to start a process,
              before we abandon and stop the whole watcher. (default: 5)
            - **hooks**: callback functions for hooking into the watcher
              startup and shutdown process. **hooks** is a dict where each key
              is the hook name and each value is a 2-tuple with the name of the
              callable or the callable itself and a boolean flag indicating if
              an exception occuring in the hook should not be ignored.
              Possible values for the hook name: *before_start*, *after_start*,
              *before_spawn*, *after_spawn*, *before_stop*, *after_stop*,
              *before_signal*, *after_signal*, *extended_stats*

        - **controller** -- the zmq entry point
          (default: 'tcp://127.0.0.1:5555')
        - **pubsub_endpoint** -- the zmq entry point for the pubsub
          (default: 'tcp://127.0.0.1:5556')
        - **stats_endpoint** -- the stats endpoint. If not provided,
          the *circusd-stats* process will not be launched. (default: None)
        - **statsd_close_outputs** -- if True sends the circusd-stats
          stdout/stderr to /dev/null (default: False)
        - **context** -- the zmq context (default: None)
        - **background** -- If True, the arbiter is launched in a thread in the
          background (default: False)
        - **stream_backend** -- the backend that will be used for the streaming
          process. Can be *thread* or *gevent*. When set to *gevent* you need
          to have *gevent* and *gevent_zmq* installed. (default: thread)
        - **plugins** -- a list of plugins. Each item is a mapping with:

            - **use** -- Fully qualified name that points to the plugin class
            - every other value is passed to the plugin in the **config**
              option

        - **debug** -- If True the arbiter is launched in debug mode
          (default: False)
        - **proc_name** -- the arbiter process name (default: circusd)
        - **loop** -- the event loop (default: None)
        - **check_delay** -- the delay between two controller points
        (default: 1 s)
        """
        from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                                 DEFAULT_ENDPOINT_MULTICAST,
                                 DEFAULT_ENDPOINT_STATS)
        if controller is None:
            controller = DEFAULT_ENDPOINT_DEALER
        if pubsub_endpoint is None:
            pubsub_endpoint = DEFAULT_ENDPOINT_SUB
        if multicast_endpoint is None:
            multicast_endpoint = DEFAULT_ENDPOINT_MULTICAST
        if stats_endpoint is None and statsd:
            stats_endpoint = DEFAULT_ENDPOINT_STATS
        elif stats_endpoint is not None and not statsd:
            warnings.warn("You defined a stats_endpoint without "
                          "setting up statsd to True.",
                          DeprecationWarning)
            statsd = True

        from circus.watcher import Watcher
        Arbiter = self._get_arbiter_klass(background=background)

        _watchers = []

        for watcher in watchers:
            cmd = watcher['cmd']
            watcher['name'] = watcher.get('name',
                                          os.path.basename(cmd.split()[0]))
            watcher['stream_backend'] = stream_backend
            _watchers.append(Watcher.load_from_config(watcher))

        return Arbiter(_watchers, controller, pubsub_endpoint,
                       httpd=httpd, statsd=statsd,
                       stats_endpoint=stats_endpoint,
                       statsd_close_outputs=statsd_close_outputs,
                       multicast_endpoint=multicast_endpoint,
                       context=context, plugins=plugins, debug=debug,
                       proc_name=proc_name, loop=loop, check_delay=check_delay,
                       **kw)

    def _get_arbiter_klass(self, background):
        if background:
            from circus.arbiter import ThreadedArbiter as Arbiter   # NOQA
        else:
            from circus.arbiter import Arbiter   # NOQA
        return Arbiter


get_arbiter = ArbiterHandler()
