import logging
import os
import sys


version_info = (0, 3, 1)
__version__ = ".".join(map(str, version_info))


logger = logging.getLogger('circus')


def get_arbiter(watchers, controller='tcp://127.0.0.1:5555',
                pubsub_endpoint='tcp://127.0.0.1:5556',
                env=None, name=None, context=None, check_flapping=True,
                background=False, stream_backend="thread"):
    """Creates a Arbiter and a single watcher in it.

    Options:

    - **watchers** -- a list of watchers. A watcher in that case is a
      dict containing:

        - **name** -- the name of the watcher (default: None)
        - **cmd** -- the command line used to run the Watcher.
        - **args** -- the args for the command (list or string).
        - **executable** -- When executable is given, the first item in
          the args sequence obtained from **cmd** is still treated by most
          programs as the command name, which can then be different from the
          actual executable name. It becomes the display name for the executing
          program in utilities such as **ps**.
        - **numprocesses** -- the number of flies to spawn (default: 1).
        - **warmup_delay** -- the delay in seconds between two spawns
          (default: 0)
        - **shell** -- if True, the flies are run in the shell
          (default: False)
        - **working_dir** - the working dir for the processes (default: None)
        - **uid** -- the user id used to run the flies (default: None)
        - **gid** -- the group id used to run the flies (default: None)
        - **env** -- the environment passed to the flies (default: None)
        - **stdout_stream**: a mapping containing the options for configuring
          the stdout stream. Default to None. When provided, may contain:
            - **class**: the fully qualified name of the class to use for
              streaming. Defaults to circus.stream.FileStream
            - **refresh_time**: the delay between two stream checks. Defaults to
              0.3 seconds.
            - any other key will be passed the class constructor.
        - **stderr_stream**: a mapping containing the options for configuring
          the stderr stream. Default to None. When provided, may contain:
            - **class**: the fully qualified name of the class to use for
              streaming. Defaults to circus.stream.FileStream
            - **refresh_time**: the delay between two stream checks. Defaults to
              0.3 seconds.
            - any other key will be passed the class constructor.

    - **controller** -- the zmq entry point (default: 'tcp://127.0.0.1:5555')
    - **pubsub_endpoint** -- the zmq entry point for the pubsub
      (default: 'tcp://127.0.0.1:5556')
    - **context** -- the zmq context (default: None)
    - **check_flapping** -- If True, the flapping detection is activated.
      (default:True)
    - **background** -- If True, the arbiter is launched in a thread in the
      background (default: False)
    - **stream_backend** -- the backend that will be used for the streaming
      process. Can be *thread* or *gevent*. When set to *gevent* you need
      to have *gevent* and *gevent_zmq* installed. (default: thread)
    """
    if stream_backend == 'gevent':
        try:
            import gevent           # NOQA
            import gevent_zeromq    # NOQA
        except ImportError:
            sys.stderr.write("stream_backend set to gevent, " +
                             "but gevent or gevent_zeromq isn't installed\n")
            sys.stderr.write("Exiting...")
            sys.exit(1)

        from gevent import monkey
        from gevent_zeromq import monkey_patch
        monkey.patch_all()
        monkey_patch()

    from circus.watcher import Watcher
    if background:
        from circus.arbiter import ThreadedArbiter as Arbiter   # NOQA
    else:
        from circus.arbiter import Arbiter   # NOQA

    _watchers = []

    for watcher in watchers:
        cmd = watcher['cmd']
        watcher['name'] = watcher.get('name', os.path.basename(cmd.split()[0]))
        watcher['stream_backend'] = stream_backend
        _watchers.append(Watcher.load_from_config(watcher))

    return Arbiter(_watchers, controller, pubsub_endpoint, context=context,
                   check_flapping=check_flapping)
