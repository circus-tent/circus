import glob
import os
import signal
import warnings
from fnmatch import fnmatch

from circus import logger
from circus.util import (DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                         DEFAULT_ENDPOINT_MULTICAST, DEFAULT_ENDPOINT_STATS,
                         StrictConfigParser, replace_gnu_args, to_signum)


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
        'stop_signal': signal.SIGTERM,
        'stop_children': False,
        'max_retry': 5,
        'graceful_timeout': 30,
        'rlimits': dict(),
        'stderr_stream': dict(),
        'stdout_stream': dict(),
        'priority': 0,
        'use_sockets': False,
        'singleton': False,
        'copy_env': False,
        'copy_path': False,
        'hooks': dict(),
        'respawn': True,
        'autostart': True}


_BOOL_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                '0': False, 'no': False, 'false': False, 'off': False}


def to_boolean(value):
    value = value.lower().strip()
    if value not in _BOOL_STATES:
        raise ValueError(value)
    return _BOOL_STATES[value]


class DefaultConfigParser(StrictConfigParser):

    def __init__(self, *args, **kw):
        StrictConfigParser.__init__(self, *args, **kw)
        self._env = dict(os.environ)

    def set_env(self, env):
        self._env = dict(env)

    def get(self, section, option):
        res = StrictConfigParser.get(self, section, option)
        return replace_gnu_args(res, env=self._env)

    def items(self, section, noreplace=False):
        items = StrictConfigParser.items(self, section)
        if noreplace:
            return items

        return [(key, replace_gnu_args(value, env=self._env))
                for key, value in items]

    def dget(self, section, option, default=None, type=str):
        if not self.has_option(section, option):
            return default

        value = self.get(section, option)

        if type is int:
            value = int(value)
        elif type is bool:
            value = self.toboolean(value)
        elif type is not str:
            raise NotImplementedError()

        return value


def read_config(config_path):
    cfg = DefaultConfigParser()
    with open(config_path) as f:
        if hasattr(cfg, 'read_file'):
            cfg.read_file(f)
        else:
            cfg.readfp(f)

    current_dir = os.path.dirname(config_path)

    # load included config files
    includes = []

    def _scan(filename, includes):
        if os.path.abspath(filename) != filename:
            filename = os.path.join(current_dir, filename)

        paths = glob.glob(filename)
        if paths == []:
            logger.warn('%r does not lead to any config. Make sure '
                        'include paths are relative to the main config '
                        'file' % filename)
        includes += paths

    for include_file in cfg.dget('circus', 'include', '').split():
        _scan(include_file, includes)

    for include_dir in cfg.dget('circus', 'include_dir', '').split():
        _scan(os.path.join(include_dir, '*.ini'), includes)

    logger.debug('Reading config files: %s' % includes)
    return cfg, [config_path] + cfg.read(includes)


def get_config(config_file):
    if not os.path.exists(config_file):
        raise IOError("the configuration file %r does not exist\n" %
                      config_file)

    cfg, cfg_files_read = read_config(config_file)
    dget = cfg.dget
    config = {}

    # reading the global environ first
    def _upper(items):
        return [(key.upper(), value) for key, value in items]

    global_env = dict(_upper(os.environ.items()))
    local_env = dict()

    # update environments with [env] section
    if 'env' in cfg.sections():
        local_env.update(dict(_upper(cfg.items('env'))))
        global_env.update(local_env)

    # always set the cfg environment
    cfg.set_env(global_env)

    # main circus options
    config['check'] = dget('circus', 'check_delay', 5, int)
    config['endpoint'] = dget('circus', 'endpoint', DEFAULT_ENDPOINT_DEALER)
    config['pubsub_endpoint'] = dget('circus', 'pubsub_endpoint',
                                     DEFAULT_ENDPOINT_SUB)
    config['multicast_endpoint'] = dget('circus', 'multicast_endpoint',
                                        DEFAULT_ENDPOINT_MULTICAST)
    config['stats_endpoint'] = dget('circus', 'stats_endpoint', None)
    config['statsd'] = dget('circus', 'statsd', False, bool)

    if config['stats_endpoint'] is None:
        config['stats_endpoint'] = DEFAULT_ENDPOINT_STATS
    elif not config['statsd']:
        warnings.warn("You defined a stats_endpoint without "
                      "setting up statsd to True.",
                      DeprecationWarning)
        config['statsd'] = True

    config['warmup_delay'] = dget('circus', 'warmup_delay', 0, int)
    config['httpd'] = dget('circus', 'httpd', False, bool)
    config['httpd_host'] = dget('circus', 'httpd_host', 'localhost', str)
    config['httpd_port'] = dget('circus', 'httpd_port', 8080, int)
    config['debug'] = dget('circus', 'debug', False, bool)
    config['pidfile'] = dget('circus', 'pidfile')
    config['loglevel'] = dget('circus', 'loglevel')
    config['logoutput'] = dget('circus', 'logoutput')
    config['fqdn_prefix'] = dget('circus', 'fqdn_prefix', None, str)

    # Initialize watchers, plugins & sockets to manage
    watchers = []
    plugins = []
    sockets = []

    for section in cfg.sections():
        if section.startswith("socket:"):
            sock = dict(cfg.items(section))
            sock['name'] = section.split("socket:")[-1].lower()
            sockets.append(sock)

        if section.startswith("plugin:"):
            plugin = dict(cfg.items(section))
            plugin['name'] = section
            plugins.append(plugin)

        if section.startswith("watcher:"):
            watcher = watcher_defaults()
            watcher['name'] = section.split("watcher:", 1)[1]

            # create watcher options
            for opt, val in cfg.items(section, noreplace=True):
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
                elif opt == 'stop_signal':
                    watcher['stop_signal'] = to_signum(val)
                elif opt == 'stop_children':
                    watcher['stop_children'] = dget(section, 'stop_children',
                                                    False, bool)
                elif opt == 'check_flapping':
                    watcher['check_flapping'] = dget(section, 'check_flapping',
                                                     True, bool)
                elif opt == 'max_retry':
                    watcher['max_retry'] = dget(section, "max_retry", 5, int)
                elif opt == 'graceful_timeout':
                    watcher['graceful_timeout'] = dget(
                        section, "graceful_timeout", 30, int)
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
                elif opt == 'copy_env':
                    watcher['copy_env'] = dget(section, "copy_env", False,
                                               bool)
                elif opt == 'copy_path':
                    watcher['copy_path'] = dget(section, "copy_path", False,
                                                bool)
                elif opt.startswith('hooks.'):
                    hook_name = opt[len('hooks.'):]
                    val = [elmt.strip() for elmt in val.split(',', 1)]
                    if len(val) == 1:
                        val.append(False)
                    else:
                        val[1] = to_boolean(val[1])

                    watcher['hooks'][hook_name] = val

                elif opt == 'respawn':
                    watcher['respawn'] = dget(section, "respawn", True, bool)

                elif opt == 'autostart':
                    watcher['autostart'] = dget(section, "autostart", True,
                                                bool)
                elif opt == 'close_child_stdout':
                    watcher['close_child_stdout'] = dget(section,
                                                         "close_child_stdout",
                                                         False, bool)
                elif opt == 'close_child_stderr':
                    watcher['close_child_stderr'] = dget(section,
                                                         "close_child_stderr",
                                                         False, bool)
                else:
                    # freeform
                    watcher[opt] = val

            if watcher['copy_env']:
                watcher['env'] = dict(global_env)
            else:
                watcher['env'] = dict(local_env)

            watchers.append(watcher)

    # Second pass to make sure env sections apply to all watchers.

    def _extend(target, source):
        for name, value in source:
            if name in target:
                continue
            target[name] = value

    def _expand_vars(target, key, env):
        if isinstance(target[key], str):
            target[key] = replace_gnu_args(target[key], env=env)
        elif isinstance(target[key], dict):
            for k in target[key].keys():
                _expand_vars(target[key], k, env)

    def _expand_section(section, env, exclude=None):
        if exclude is None:
            exclude = ('name', 'env')

        for option in section.keys():
            if option in exclude:
                continue
            _expand_vars(section, option, env)

    # build environment for watcher sections
    for section in cfg.sections():
        if section.startswith('env:'):
            section_elements = section.split("env:", 1)[1]
            watcher_patterns = [s.strip() for s in section_elements.split(',')]
            env_items = dict(_upper(cfg.items(section, noreplace=True)))

            for pattern in watcher_patterns:
                match = [w for w in watchers if fnmatch(w['name'], pattern)]

                for watcher in match:
                    watcher['env'].update(env_items)

    # expand environment for watcher sections
    for watcher in watchers:
        env = dict(global_env)
        env.update(watcher['env'])
        _expand_section(watcher, env)

    config['watchers'] = watchers
    config['plugins'] = plugins
    config['sockets'] = sockets
    return config
