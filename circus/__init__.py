import logging
import os

version_info = (0, 1, 0)
__version__ = ".".join(map(str, version_info))


logger = logging.getLogger('circus')


def get_trainer(cmd, numflies=1.,
                warmup_delay=0., controller='tcp://127.0.0.1:5555',
                pubsub_endpoint='tcp://127.0.0.1:5556',
                shell=False, working_dir=None, uid=None, gid=None,
                env=None, name=None, context=None):
    """Creates a Trainer and a single show in it.

    Options:

    - cmd: the command line used to run the Show.
    - numflies: the number of flies to spawn (default: 1).
    - warmup_delay: the delay in seconds between two spawns (default: 0)
    - controller: the zmq entry point (default: 'tcp://127.0.0.1:5555')
    - pubsub_endpoint: the zmq entry point for the pubsub (default:
      'tcp://127.0.0.1:5556')
    - shell: if True, the flies are run in the shell (default: False)
    - working_dir: the working dir for the flies (default: None)
    - uid: the user id used to run the flies (default: None)
    - gid: the group id used to run the flies (default: None)
    - env: the environment passed to the flies (default: None)
    - name: the name of the show (default: None)

    """
    from circus.show import Show
    from circus.trainer import Trainer

    if not name:
        name = os.path.basename(cmd.split(None)[0])

    show = Show(name, cmd, numflies, working_dir=working_dir,
                warmup_delay=warmup_delay, shell=shell, uid=uid, gid=gid,
                env=env)
    return Trainer([show], controller, pubsub_endpoint, context=context)
