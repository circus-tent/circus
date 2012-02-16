# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import argparse
import ConfigParser
import os
import logging

from circus import logger
from circus.trainer import Trainer
from circus.show import Show


LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG}

LOG_FMT = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
LOG_DATE_FMT = r"%Y-%m-%d %H:%M:%S"

class DefaultConfigParser(ConfigParser.ConfigParser):
    def dget(self, section, option, default=None, type=str):
        if not self.has_option(section, option):
            return default
        if type is str:
            return self.get(section, option)
        elif type is int:
            return self.getint(section, option)
        elif type is bool:
            return self.getboolean(section, option)
        else:
            raise NotImplementedError()


def main():
    parser = argparse.ArgumentParser(description='Run some shows.')
    parser.add_argument('config', help='configuration file')
    parser.add_argument('--log-level', dest='loglevel', default='info',
            help="log level")
    parser.add_argument('--log-output', dest='logoutput', default='-',
            help="log output")
    args = parser.parse_args()
    cfg = DefaultConfigParser()
    cfg.read(args.config)

    # configure the logger
    loglevel = LOG_LEVELS.get(args.loglevel.lower(), logging.INFO)
    logger.setLevel(loglevel)
    if args.logoutput == "-":
        h = logging.StreamHandler()
    else:
        h = logging.FileHandler(output)
    fmt = logging.Formatter(LOG_FMT, LOG_DATE_FMT)
    h.setFormatter(fmt)
    logger.addHandler(h)

    # Initialize shows to manage
    shows = []
    for section in cfg.sections():
        if section.startswith("show:"):
            name = section.split("show:", 1)[1]

            cmd = cfg.get(section, 'cmd')
            args = cfg.dget(section, 'args', '')
            if args:
                cmd = "%s %s" % (cmd, args)

            num_flies = cfg.dget(section, 'num_flies', 1, int)
            warmup_delay = cfg.dget(section, 'warmup_delay', 0, int)

            working_dir = cfg.dget(section, 'working_dir', os.getcwd())
            shell = cfg.dget(section, 'shell', False, bool)
            uid = cfg.dget(section, 'uid')
            gid = cfg.dget(section, 'gid')
            send_hup = cfg.dget(section, 'send_hup', False, bool)
            shows.append(Show(name, cmd, num_flies, warmup_delay, working_dir,
                              shell, uid, gid, send_hup))

    check = cfg.dget('circus', 'check_delay', 5, int)
    endpoint = cfg.dget('circus', 'endpoint', 'tcp://127.0.0.1:5555')
    ipc_prefix = cfg.dget('circus', 'ipc_prefix')
    trainer = Trainer(shows, check, endpoint, ipc_prefix)
    try:
        trainer.run()
    finally:
        trainer.terminate()


if __name__ == '__main__':
    main()
