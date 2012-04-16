import ConfigParser
import os
import fnmatch
import sys

from circus.stream import FileStream
from circus import util


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


def read_config(config_path):
    cfg = DefaultConfigParser()
    with open(config_path) as f:
        cfg.readfp(f)
    cfg_files_read = [config_path]

    # load included config files
    includes = []
    for include_file in cfg.dget('circus', 'include', '').split():
        includes.append(include_file)

    for include_dir in cfg.dget('circus', 'include_dir', '').split():
        for root, dirnames, filenames in os.walk(include_dir):
            for filename in fnmatch.filter(filenames, '*.ini'):
                cfg_file = os.path.join(root, filename)
                includes.append(cfg_file)

    cfg_files_read.extend(cfg.read(includes))

    return cfg, cfg_files_read


def get_config(config_file):
    cfg, cfg_files_read = read_config(config_file)
    dget = cfg.dget
    get = cfg.get
    config = {}

    # main circus options
    config['check'] = dget('circus', 'check_delay', 5, int)
    config['endpoint'] = dget('circus', 'endpoint', 'tcp://127.0.0.1:5555')
    config['pubsub_endpoint'] = dget('circus', 'pubsub_endpoint',
                                     'tcp://127.0.0.1:5556')

    stream_backend = dget('circus', 'stream_backend', 'thread')
    if stream_backend == 'gevent':
        try:
            import gevent
            import gevent_zeromq
        except ImportError:
            sys.stderr.write("stream_backend set to gevent, " +
                             "but gevent or gevent_zeromq isn't installed\n")
            sys.stderr.write("Exiting...")
            sys.exit(1)

        from gevent import monkey
        from gevent_zeromq import monkey_patch
        monkey.patch_all()
        monkey_patch()

    config['stream_backend'] = stream_backend

    # Initialize watchers to manage
    watchers = []
    for section in cfg.sections():
        if section.startswith("watcher:"):
            watcher = {}
            watcher['name'] = section.split("watcher:", 1)[1]
            watcher['cmd'] = get(section, 'cmd')
            watcher['args'] = dget(section, 'args', '')
            watcher['numprocesses'] = dget(section, 'numprocesses', 1, int)
            watcher['warmup_delay'] = dget(section, 'warmup_delay', 0, int)
            watcher['executable'] = dget(section, 'executable', None, str)
            watcher['working_dir'] = dget(section, 'working_dir')
            watcher['shell'] = dget(section, 'shell', False, bool)
            watcher['uid '] = dget(section, 'uid')
            watcher['gid'] = dget(section, 'gid')
            watcher['send_hup'] = dget(section, 'send_hup', False, bool)
            watcher['times'] = dget(section, "times", 2, int)
            watcher['within'] = dget(section, "within", 1, int)
            watcher['retry_in'] = dget(section, "retry_in", 7, int)
            watcher['max_retry'] = dget(section, "max_retry", 5, int)
            watcher['graceful_timeout'] = dget(section, "graceful_timeout", 30,
                                               int)

            # loading the streams

            stderr_file = dget(section, 'stderr_file', None, str)
            stdout_file = dget(section, 'stdout_file', None, str)
            stderr_stream = dget(section, 'stderr_stream', None, str)
            stdout_stream = dget(section, 'stdout_stream', None, str)

            if stderr_stream is not None and stderr_file is not None:
                raise ValueError('"stderr_stream" and "stderr_file" are '
                                 'mutually exclusive')

            if stdout_stream is not None and stdout_file is not None:
                raise ValueError('"stdout_stream" and "stdout_file" are '
                                 'mutually exclusive')

            if stderr_file is not None:
                watcher['stderr_stream'] = FileStream(stderr_file)
            elif stderr_stream is not None:
                watcher['stderr_stream '] = util.resolve_name(stderr_stream)

            if stdout_file is not None:
                watcher['stdout_stream'] = FileStream(stdout_file)
            elif stdout_stream is not None:
                watcher['stdout_stream'] = util.resolve_name(stdout_stream)

            rlimits = {}
            for cfg_name, cfg_value in cfg.items(section):
                if cfg_name.startswith('rlimit_'):
                    limit = cfg_name[7:]
                    rlimits[limit] = int(cfg_value)

            watcher['rlimits'] = rlimits

            watchers.append(watcher)

    config['watchers'] = watchers


    return config
