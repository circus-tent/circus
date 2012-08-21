import os
import fnmatch
import sys

from circus import logger
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                         DEFAULT_CLUSTER_DEALER, StrictConfigParser)


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
        'max_retry': 5,
        'graceful_timeout': 30,
        'rlimits': dict(),
        'stderr_stream': dict(),
        'stdout_stream': dict(),
        'priority': 0,
        'use_sockets': False,
        'singleton': False,
        'copy_env': False,
        'copy_path': False}


class DefaultConfigParser(StrictConfigParser):
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

    current_dir = os.path.dirname(config_path)

    # load included config files
    includes = []

    def include_filename(filename):
        if '*' in filename:
            include_dir = os.path.dirname(filename)
            if os.path.abspath(filename) != filename:
                include_dir = os.path.join(current_dir,
                                           os.path.dirname(filename))

            wildcard = os.path.basename(filename)
            for root, dirnames, filenames in os.walk(include_dir):
                for filename in fnmatch.filter(filenames, wildcard):
                    cfg_file = os.path.join(root, filename)
                    includes.append(cfg_file)

        elif os.path.isfile(filename):
            includes.append(filename)

    for include_file in cfg.dget('circus', 'include', '').split():
        include_filename(include_file)

    for include_dir in cfg.dget('circus', 'include_dir', '').split():
        include_filename(os.path.join(include_dir, '*.ini'))

    logger.debug('reading config files: %s' % includes)

    cfg_files_read.extend(cfg.read(includes))

    return cfg, cfg_files_read

def load_circus_options(config, section, dget):
    config['check'] = dget(section, 'check_delay', 5, int)
    config['endpoint'] = dget(section, 'endpoint',
                              DEFAULT_ENDPOINT_DEALER
                              if section == 'circus'
                              else DEFAULT_CLUSTER_DEALER)
    config['pubsub_endpoint'] = dget(section, 'pubsub_endpoint',
                                     DEFAULT_ENDPOINT_SUB
                                     if section == 'circus'
                                     else None)
    config['stats_endpoint'] = dget(section, 'stats_endpoint', None, str)
    config['warmup_delay'] = dget(section, 'warmup_delay', 0, int)
    config['httpd'] = dget(section, 'httpd', False, bool)
    config['httpd_host'] = dget(section, 'httpd_host', 'localhost', str)
    config['httpd_port'] = dget(section, 'httpd_port', 8080, int)
    config['debug'] = dget(section, 'debug', False, bool)
    config['node'] = dget(section, 'node', None, str)
    config['master'] = dget(section, 'master', DEFAULT_CLUSTER_DEALER, str)

def get_config(config_file):
    if not os.path.exists(config_file):
        sys.stderr.write("the configuration file %r does not exist\n" %
                config_file)
        sys.stderr.write("Exiting...\n")
        sys.exit(1)

    cfg, cfg_files_read = read_config(config_file)
    dget = cfg.dget
    config = {}

    # main circus options
    load_circus_options(config, 'circus', dget)
    
    # main circus cluster options
    config['cluster'] = {}
    load_circus_options(config['cluster'], 'circus-cluster', dget)
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

    # Initialize watchers, plugins & sockets to manage
    watchers = []
    plugins = []
    sockets = []
    nodes = []

    for section in cfg.sections():
        if section.startswith("socket:"):
            sock = dict(cfg.items(section))
            sock['name'] = section.split("socket:")[-1].lower()
            sockets.append(sock)

        if section.startswith("plugin:"):
            plugins.append(dict(cfg.items(section)))

        if section.startswith("node:"):
            node = {}
            node['name'] = section.split("node:", 1)[1]
            for opt, val in cfg.items(section):
                if opt == 'endpoint':
                    node['endpoint'] = val
                elif opt == 'stats_endpoint':
                    node['stats_endpoint'] = val
            nodes.append(node)

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
                    watcher['uid'] = val
                elif opt == 'gid':
                    watcher['gid'] = val
                elif opt == 'send_hup':
                    watcher['send_hup'] = dget(section, 'send_hup', False,
                            bool)
                elif opt == 'check_flapping':
                    watcher['check_flapping'] = dget(section, 'check_flapping',
                                                     True, bool)
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
                elif opt == 'priority':
                    watcher['priority'] = dget(section, "priority", 0, int)
                elif opt == 'use_sockets':
                    watcher['use_sockets'] = dget(section, "use_sockets",
                                                  False, bool)
                elif opt == 'singleton':
                    watcher['singleton'] = dget(section, "singleton", False,
                                                bool)
                elif opt == 'stream_backend':
                    watcher['stream_backend'] = val
                elif opt == 'copy_env':
                    watcher['copy_env'] = dget(section, "copy_env", False,
                                                bool)
                elif opt == 'copy_path':
                    watcher['copy_path'] = dget(section, "copy_path", False,
                                                bool)

                else:
                    # freeform
                    watcher[opt] = val

            # set the stream backend
            if 'stream_backend' not in watcher:
                watcher['stream_backend'] = stream_backend
            watchers.append(watcher)

    config['watchers'] = watchers
    config['plugins'] = plugins
    config['sockets'] = sockets
    config['nodes'] = nodes
    return config
