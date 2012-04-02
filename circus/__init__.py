import logging
import os

version_info = (0, 1, 0)
__version__ = ".".join(map(str, version_info))


logger = logging.getLogger('circus')


def get_arbiter(watchers, controller='tcp://127.0.0.1:5555',
                pubsub_endpoint='tcp://127.0.0.1:5556',
                env=None, name=None, context=None,
                check_flapping=True, background=False):
    """Creates a Arbiter and a single watcher in it.

    Options:

    - **watchers** -- a list of watchers. A watcher in that case is a
      dict containing:

        - **name** -- the name of the watcher (default: None)
        - **cmd** -- the command line used to run the Watcher.
        - **args** -- the args for the command (list or string).
        - **executable**: When executable is given, the first item in
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

    - **controller** -- the zmq entry point (default: 'tcp://127.0.0.1:5555')
    - **pubsub_endpoint** -- the zmq entry point for the pubsub
      (default: 'tcp://127.0.0.1:5556')
    - **context** -- the zmq context (default: None)
    - **check_flapping** -- If True, the flapping detection is activated.
      (default:True)
    - **background** -- If True, the arbiter is launched in a thread in the
      background (default: False)
    """
    from circus.watcher import Watcher
    if background:
        from circus.arbiter import ThreadedArbiter as Arbiter   # NOQA
    else:
        from circus.arbiter import Arbiter   # NOQA

    _watchers = []

    for watcher in watchers:
        cmd = watcher['cmd']
        name = watcher.get('name', os.path.basename(cmd.split()[0]))

        watcher = Watcher(name,
                          cmd,
                          args=watcher.get('args'),
                          numprocesses=watcher.get('numprocesses', 1),
                          working_dir=watcher.get('working_dir'),
                          warmup_delay=float(watcher.get('warmup_delay', '0')),
                          shell=watcher.get('shell'),
                          uid=watcher.get('uid'),
                          gid=watcher.get('gid'),
                          env=watcher.get('env'),
                          executable=watcher.get('executable'))
        _watchers.append(watcher)

    return Arbiter(_watchers, controller, pubsub_endpoint, context=context,
                   check_flapping=check_flapping)
