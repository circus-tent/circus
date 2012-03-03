import logging
from circus.util import get_working_dir

logger = logging.getLogger('circus')


def get_trainer(name, cmd, num_workers=1., timeout=1.0, check=5.,
                warmup_delay=0., controller='tcp://127.0.0.1:5555',
                shell=False, working_dir=None, uid=None, gid=None, env=None):
    from circus.show import Show
    from circus.trainer import Trainer
    show = Show(name, cmd, num_workers, working_dir=working_dir,
                 warmup_delay=warmup_delay, shell=shell, uid=uid, gid=gid,
                 env=env)
    return Trainer([show], controller)
