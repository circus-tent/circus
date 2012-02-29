import logging
from circus.util import get_working_dir

logger = logging.getLogger('circus')


def get_trainer(cmd, num_workers=5., timeout=1.0, check=5., warmup_delay=1.,
                controller='tcp://127.0.0.1:5555',
                working_dir=get_working_dir()):

    from circus.show import Show
    from circus.trainer import Trainer
    show = Show('Powerhose Workers', cmd, num_workers, working_dir=working_dir,
                 warmup_delay=warmup_delay)
    return Trainer([show], controller)
