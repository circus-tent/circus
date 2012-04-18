import ConfigParser
import os
import fnmatch
import sys

from circus.stream import FileStream
from circus import util

def watcher_defaults():
 return {
        'name': '',
        'cmd': '',
        'args': '',
        'numprocesses': 1,
        'warmup_delay': 0,
        'executable': None,
        'working_dir': None,
        'shell': False,
        'uid': None,
        'gid': None,
        'send_hup': False,
        'times': 2,
        'within': 1,
        'retry_in': 7,
        'max_retry': 5,
        'graceful_timeout': 30,
        'rlimits': dict(),
        'stderr_stream': dict(),
        'stdout_stream': dict(),
        'stream_backend': 'thread'}


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


def stream_config(watcher_name, stream_conf):
    if not stream_conf:
        return stream_conf

    if not 'class' in stream_conf:
        # we can handle othe class there
        if 'filename' in stream_conf:
            obj = FileStream
        else:
            raise ValueError("stream configuration invalid in %r" %
                    watcher_name)

    else:
        class_name = stream_conf.pop('class')
        if not "." in class_name:
            class_name = "circus.stream.%s" % class_name

        obj = util.resolve_name(class_name)

    # default refres_time
    if not 'refresh_time' in stream_conf:
        refresh_time = 0.3
    else:
        refresh_time = float(stream_conf.pop('refresh_time'))

    # initialize stream instance
    inst = obj(**stream_conf)

    return {'stream': inst, 'refresh_time': refresh_time}


def get_config(config_file):
    cfg, cfg_files_read = read_config(config_file)
    dget = cfg.dget
    config = {}

    # main circus options
    config['check'] = dget('circus', 'check_delay', 5, int)
    config['endpoint'] = dget('circus', 'endpoint', 'tcp://127.0.0.1:5555')
    config['pubsub_endpoint'] = dget('circus', 'pubsub_endpoint',
                                     'tcp://127.0.0.1:5556')

    stream_backend = dget('circus', 'stream_backend', 'thread')
    if stream_backend == 'gevent':
        try:
            import gevent           # NOQA
            import gevent_zeromq    # NOQA
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
            watcher = watcher_defaults()
            watcher['name'] = section.split("watcher:", 1)[1]

            # create watcher options
            for opt, val in cfg.items(section):
                if opt == 'cmd':
                    watcher['cmd'] = val
                elif opt == 'args':
                    watcher['args'] = val
                elif opt == 'numprocesses':
                    watcher['numprocesses'] = dget(section, 'numprocesses', 1,
                            int)
                elif opt == 'warmup_delay':
                    watcher['warmup_delay'] = dget(section, 'warmup_delay', 0,
                            int)
                elif opt == 'executable':
                    watcher['executable'] = dget(section, 'executable', None,
                            str)
                elif opt == 'working_dir':
                    watcher['working_dir'] = val
                elif opt == 'shell':
                    watcher['shell'] = dget(section, 'shell', False, bool)
                elif opt == 'uid':
                    watcher['uid '] = val
                elif opt == 'gid':
                    watcher['gid'] = val
                elif opt == 'send_hup':
                    watcher['send_hup'] = dget(section, 'send_hup', False,
                            bool)
                elif opt == 'times':
                    watcher['times'] = dget(section, "times", 2, int)
                elif opt == 'within':
                    watcher['within'] = dget(section, "within", 1, int)
                elif opt == 'retry_ind':
                    watcher['retry_in'] = dget(section, "retry_in", 7, int)
                elif opt == 'max_retry':
                    watcher['max_retry'] = dget(section, "max_retry", 5, int)
                elif opt == 'graceful_timout':
                    watcher['graceful_timeout'] = dget(section,
                            "graceful_timeout", 30, int)
                elif opt.startswith('stderr_stream') or \
                        opt.startswith('stdout_stream'):
                    stream_name, stream_opt = opt.split(".", 1)
                    watcher[stream_name][stream_opt] = val
                elif opt.startswith('rlimit_'):
                    limit = opt[7:]
                    watcher['rlimits'][limit] = int(val)

            # second pass, parse stream conf
            stdout_conf = watcher.get('stdout_stream', {})
            watcher['stdout_stream'] = stream_config(watcher['name'],
                stdout_conf)

            stderr_conf = watcher.get('stderr_stream', {})
            watcher['stderr_stream'] = stream_config(watcher['name'],
                stderr_conf)

            # set the stream backend
            watcher['stream_backend'] = stream_backend

            watchers.append(watcher)

    config['watchers'] = watchers
    return config
