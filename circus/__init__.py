import logging

logger = logging.getLogger('circus')


def get_trainer(cmd, num_workers=5., timeout=1.0, check=5.,
                controller='tcp://127.0.0.1:5555'):

    from circus.show import Show
    from circus.trainer import Trainer
    show = Show('Powerhose Workers', cmd, num_workers)
    return Trainer([show], controller)
