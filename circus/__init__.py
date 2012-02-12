import argparse
import ConfigParser

from circus.manager import Manager, Program


def main():
    parser = argparse.ArgumentParser(description='Run some programs.')
    parser.add_argument('config', help='configuration file')
    args = parser.parse_args()
    cfg = ConfigParser.ConfigParser()
    cfg.read(args.config)

    # Initialize programs to manage
    programs = []
    for section in cfg.sections():
        if section.startswith("program:"):
            cmd = cfg.get(section, 'cmd') + ' ' + cfg.get(section, 'args')
            num_workers = int(cfg.get(section, 'num-workers'))
            warmup_delay = int(cfg.get(section, 'warmup_delay'))
            programs.append(Program(cmd, num_workers, warmup_delay))

    check = int(cfg.get('circus', 'check_delay'))
    endpoint = cfg.get('circus', 'endpoint')
    if cfg.has_option('circus', 'ipc_prefix'):
        ipc_prefix = cfg.get('circus', 'ipc_prefix')
    else:
        ipc_prefix = None

    manager = Manager(programs, check, endpoint, ipc_prefix)
    try:
        manager.run()
    finally:
        manager.terminate()


if __name__ == '__main__':
    main()
