# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import argparse
import ConfigParser
import os

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
            num_flies = cfg.getint(section, 'num_flies')
            warmup_delay = cfg.getint(section, 'warmup_delay')
            if cfg.has_option(section, 'working_dir'):
                working_dir = cfg.get(section, 'working_dir')
            else:
                working_dir = os.getcwd()
            if cfg.has_option(section, 'shell'):
                shell = cfg.getboolean(section, 'shell')
            else:
                shell = False

            shows.append(Show(name, cmd, num_flies, warmup_delay, working_dir,
                              shell))

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
