import argparse
import ConfigParser

from circus.trainer import Trainer
from circus.show import Show


def main():
    parser = argparse.ArgumentParser(description='Run some shows.')
    parser.add_argument('config', help='configuration file')
    args = parser.parse_args()
    cfg = ConfigParser.ConfigParser()
    cfg.read(args.config)

    # Initialize shows to manage
    shows = []
    for section in cfg.sections():
        if section.startswith("show:"):
            name = section.split("show:", 1)[1]
            cmd = cfg.get(section, 'cmd') + ' ' + cfg.get(section, 'args')
            num_flies = int(cfg.get(section, 'num_flies'))
            warmup_delay = int(cfg.get(section, 'warmup_delay'))
            shows.append(Show(name, cmd, num_flies, warmup_delay))

    check = int(cfg.get('circus', 'check_delay'))
    endpoint = cfg.get('circus', 'endpoint')
    if cfg.has_option('circus', 'ipc_prefix'):
        ipc_prefix = cfg.get('circus', 'ipc_prefix')
    else:
        ipc_prefix = None

    trainer = Trainer(shows, check, endpoint, ipc_prefix)
    try:
        trainer.run()
    finally:
        trainer.terminate()


if __name__ == '__main__':
    main()
