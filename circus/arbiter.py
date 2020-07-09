import errno
import logging
import os
import time
import gc
from circus.fixed_threading import Thread, get_ident
import sys
import select
import socket
from tornado import gen

import zmq
from tornado import ioloop

from circus.controller import Controller
from circus.exc import AlreadyExist
from circus import logger
from circus.watcher import Watcher
from circus.util import debuglog, _setproctitle, parse_env_dict
from circus.util import DictDiffer, synchronized, tornado_sleep, papa
from circus.util import IS_WINDOWS
from circus.config import get_config
from circus.plugins import get_plugin_cmd
from circus.sockets import CircusSocket, CircusSockets


_ENV_EXCEPTIONS = ('__CF_USER_TEXT_ENCODING', 'PS1', 'COMP_WORDBREAKS',
                   'PROMPT_COMMAND')


class Arbiter(object):

    """Class used to control a list of watchers.

    Options:

    - **watchers** -- a list of Watcher objects
    - **endpoint** -- the controller ZMQ endpoint
    - **pubsub_endpoint** -- the pubsub endpoint
    - **statsd** -- If True, a circusd-stats process is run (default: False)
    - **stats_endpoint** -- the stats endpoint.
    - **statsd_close_outputs** -- if True sends the circusd-stats stdout/stderr
      to /dev/null (default: False)
    - **multicast_endpoint** -- the multicast endpoint for circusd cluster
      auto-discovery (default: udp://237.219.251.97:12027)
      Multicast addr should be between 224.0.0.0 to 239.255.255.255 and the
      same for the all cluster.
    - **check_delay** -- the delay between two controller points
      (default: 1 s)
    - **prereload_fn** -- callable that will be executed on each reload
      (default: None)
    - **context** -- if provided, the zmq context to reuse.
      (default: None)
    - **loop**: if provided, a :class:`zmq.eventloop.ioloop.IOLoop` instance
       to reuse. (default: None)
    - **plugins** -- a list of plugins. Each item is a mapping with:

        - **use** -- Fully qualified name that points to the plugin class
        - every other value is passed to the plugin in the **config** option
    - **sockets** -- a mapping of sockets. Each key is the socket name,
      and each value a :class:`CircusSocket` class. (default: None)
    - **warmup_delay** -- a delay in seconds between two watchers startup.
      (default: 0)
    - **httpd** -- If True, a circushttpd process is run (default: False)
    - **httpd_host** -- the circushttpd host (default: localhost)
    - **httpd_port** -- the circushttpd port (default: 8080)
    - **httpd_close_outputs** -- if True, sends circushttpd stdout/stderr
      to /dev/null. (default: False)
    - **debug** -- if True, adds a lot of debug info in the stdout (default:
      False)
    - **debug_gc** -- if True, does gc.set_debug(gc.DEBUG_LEAK) (default:
      False)
      to circusd to analyze problems (default: False)
    - **proc_name** -- the arbiter process name
    - **fqdn_prefix** -- a prefix for the unique identifier of the circus
                         instance on the cluster.
    - **endpoint_owner** -- unix user to chown the endpoint to if using ipc.
    - **papa_endpoint** -- the papa process kernel endpoint
    """

    def __init__(self, watchers, endpoint, pubsub_endpoint, check_delay=1.0,
                 prereload_fn=None, context=None, loop=None, statsd=False,
                 stats_endpoint=None, statsd_close_outputs=False,
                 multicast_endpoint=None, plugins=None,
                 sockets=None, warmup_delay=0, httpd=False,
                 httpd_host='localhost', httpd_port=8080,
                 httpd_close_outputs=False, debug=False, debug_gc=False,
                 ssh_server=None, proc_name='circusd', pidfile=None,
                 loglevel=None, logoutput=None, loggerconfig=None,
                 fqdn_prefix=None, umask=None, endpoint_owner=None,
                 papa_endpoint=None):

        self.watchers = watchers
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.prereload_fn = prereload_fn
        self.pubsub_endpoint = pubsub_endpoint
        self.multicast_endpoint = multicast_endpoint
        self.proc_name = proc_name
        self.ssh_server = ssh_server
        self.evpub_socket = None
        self.pidfile = pidfile
        self.loglevel = loglevel
        self.logoutput = logoutput
        self.loggerconfig = loggerconfig
        self.umask = umask
        self.endpoint_owner = endpoint_owner
        self._running = False
        try:
            # getfqdn appears to fail in Python3.3 in the unittest
            # framework so fall back to gethostname
            socket_fqdn = socket.getfqdn()
        except KeyError:
            socket_fqdn = socket.gethostname()
        if fqdn_prefix is None:
            fqdn = socket_fqdn
        else:
            fqdn = '{}@{}'.format(fqdn_prefix, socket_fqdn)
        self.fqdn = fqdn

        if papa_endpoint and papa:
            if papa_endpoint.startswith('ipc:/'):
                papa_endpoint = papa_endpoint[4:]
                while papa_endpoint[:2] == '//':
                    papa_endpoint = papa_endpoint[1:]
                papa.set_default_path(papa_endpoint)
            elif papa_endpoint.startswith('tcp://'):
                papa_endpoint = papa_endpoint[6:].partition(':')[2]
                papa.set_default_port = papa_endpoint

        self.ctrl = self.loop = None
        self._provided_loop = False
        self.socket_event = False
        if loop is not None:
            self._provided_loop = True
            self.loop = loop

        # initialize zmq context
        self._init_context(context)
        self.pid = os.getpid()
        self._watchers_names = {}
        self._stopping = False
        self._restarting = False
        self.debug = debug
        self._exclusive_running_command = None
        if self.debug:
            self.stdout_stream = self.stderr_stream = {'class': 'StdoutStream'}
        else:
            self.stdout_stream = self.stderr_stream = None

        self.debug_gc = debug_gc
        if debug_gc:
            gc.set_debug(gc.DEBUG_LEAK)

        # initializing circusd-stats as a watcher when configured
        self.statsd = statsd
        self.stats_endpoint = stats_endpoint

        if self.statsd:
            cmd = "%s -c 'from circus import stats; stats.main()'" % \
                sys.executable
            cmd += ' --endpoint %s' % self.endpoint
            cmd += ' --pubsub %s' % self.pubsub_endpoint
            cmd += ' --statspoint %s' % self.stats_endpoint
            if ssh_server is not None:
                cmd += ' --ssh %s' % ssh_server
            if debug:
                cmd += ' --log-level DEBUG'
            elif self.loglevel:
                cmd += ' --log-level ' + self.loglevel
            if self.logoutput:
                cmd += ' --log-output ' + self.logoutput
            stats_watcher = Watcher('circusd-stats', cmd, use_sockets=True,
                                    singleton=True,
                                    stdout_stream=self.stdout_stream,
                                    stderr_stream=self.stderr_stream,
                                    copy_env=True, copy_path=True,
                                    close_child_stderr=statsd_close_outputs,
                                    close_child_stdout=statsd_close_outputs)

            self.watchers.append(stats_watcher)

        # adding the httpd
        if httpd:
            # adding the socket
            httpd_socket = CircusSocket(name='circushttpd', host=httpd_host,
                                        port=httpd_port)
            if sockets is None:
                sockets = [httpd_socket]
            else:
                sockets.append(httpd_socket)

            cmd = ("%s -c 'from circusweb import circushttpd; "
                   "circushttpd.main()'") % sys.executable
            cmd += ' --endpoint %s' % self.endpoint
            cmd += ' --fd $(circus.sockets.circushttpd)'
            if ssh_server is not None:
                cmd += ' --ssh %s' % ssh_server

            # Adding the watcher
            httpd_watcher = Watcher('circushttpd', cmd, use_sockets=True,
                                    singleton=True,
                                    stdout_stream=self.stdout_stream,
                                    stderr_stream=self.stderr_stream,
                                    copy_env=True, copy_path=True,
                                    close_child_stderr=httpd_close_outputs,
                                    close_child_stdout=httpd_close_outputs)
            self.watchers.append(httpd_watcher)

        # adding each plugin as a watcher
        ch_stderr = self.stderr_stream is None
        ch_stdout = self.stdout_stream is None

        if plugins is not None:
            for plugin in plugins:
                fqn = plugin['use']
                cmd = get_plugin_cmd(plugin, self.endpoint,
                                     self.pubsub_endpoint, self.check_delay,
                                     ssh_server, debug=self.debug,
                                     loglevel=self.loglevel,
                                     logoutput=self.logoutput)
                plugin_cfg = dict(cmd=cmd, priority=1, singleton=True,
                                  stdout_stream=self.stdout_stream,
                                  stderr_stream=self.stderr_stream,
                                  copy_env=True, copy_path=True,
                                  close_child_stderr=ch_stderr,
                                  close_child_stdout=ch_stdout)
                plugin_cfg.update(plugin)
                if 'name' not in plugin_cfg:
                    plugin_cfg['name'] = fqn

                plugin_watcher = Watcher.load_from_config(plugin_cfg)
                self.watchers.append(plugin_watcher)

        self.sockets = CircusSockets(sockets)
        self.warmup_delay = warmup_delay

    @property
    def running(self):
        return self._running

    def _init_context(self, context):
        self.context = context or zmq.Context.instance()
        if self.loop is None:
            self.loop = ioloop.IOLoop.current()
        self.ctrl = Controller(self.endpoint, self.multicast_endpoint,
                               self.context, self.loop, self, self.check_delay,
                               self.endpoint_owner)

    def get_socket(self, name):
        return self.sockets.get(name, None)

    def get_watcher_config(self, config, name):
        for i in config.get('watchers', []):
            if i['name'] == name:
                return i.copy()
        return None

    def get_plugin_config(self, config, name):
        for i in config.get('plugins', []):
            if i['name'] == name:
                cfg = i.copy()
                cmd = get_plugin_cmd(cfg, self.endpoint,
                                     self.pubsub_endpoint, self.check_delay,
                                     self.ssh_server, debug=self.debug)

                cfg.update(dict(cmd=cmd, priority=1, singleton=True,
                                stdout_stream=self.stdout_stream,
                                stderr_stream=self.stderr_stream,
                                copy_env=True, copy_path=True))
                return cfg
        return None

    @classmethod
    def get_arbiter_config(cls, config):
        cfg = config.copy()
        del cfg['watchers']
        del cfg['plugins']
        del cfg['sockets']

        return cfg

    @synchronized("arbiter_reload_config")
    @gen.coroutine
    def reload_from_config(self, config_file=None, inside_circusd=False):
        new_cfg = get_config(config_file if config_file else self.config_file)
        # if arbiter is changed, reload everything
        if self.get_arbiter_config(new_cfg) != self._cfg:
            yield self._restart(inside_circusd=inside_circusd)
            return

        ignore_sn = set(['circushttpd'])
        ignore_wn = set(['circushttpd', 'circusd-stats'])

        # Gather socket names.
        current_sn = set([i.name for i in self.sockets.values()]) - ignore_sn
        new_sockets = dict(
            (i['name'], i.copy()) for i in new_cfg.get('sockets', [])
        )
        new_sn = set(new_sockets.keys())
        added_sn = new_sn - current_sn
        deleted_sn = current_sn - new_sn
        maybechanged_sn = current_sn - deleted_sn
        changed_sn = set([])
        wn_with_changed_socket = set([])
        wn_with_deleted_socket = set([])

        # get changed sockets
        for n in maybechanged_sn:
            s = self.get_socket(n)
            if new_sockets[n] != s._cfg:
                changed_sn.add(n)

                # just delete the socket and add it again
                deleted_sn.add(n)
                added_sn.add(n)

                # Get the watchers whichs use these, so they could be
                # deleted and added also
                for w in self.iter_watchers():
                    if 'circus.sockets.%s' % n.lower() in w.cmd:
                        wn_with_changed_socket.add(w.name)

        # get deleted sockets
        for n in deleted_sn:
            s = self.get_socket(n)
            s.close()
            # Get the watchers whichs use these, these should not be
            # active anymore
            for w in self.iter_watchers():
                if 'circus.sockets.%s' % n.lower() in w.cmd:
                    wn_with_deleted_socket.add(w.name)
            del self.sockets[s.name]

        # get added sockets
        for n in added_sn:
            socket_config = new_sockets[n]
            s = CircusSocket.load_from_config(socket_config)
            s.bind_and_listen()
            self.sockets[s.name] = s

        if added_sn or deleted_sn:
            # make sure all existing watchers get the new sockets in
            # their attributes and get the old removed
            # XXX: is this necessary? self.sockets is an mutable
            # object
            for watcher in self.iter_watchers():
                # XXX: What happens as initalize is called on a
                # running watcher?
                watcher.initialize(self.evpub_socket, self.sockets, self)

        # Gather watcher names.
        current_wn = set([i.name for i in self.iter_watchers()]) - ignore_wn
        new_wn = set([i['name'] for i in new_cfg.get('watchers', [])])
        new_wn = new_wn | set([i['name'] for i in new_cfg.get('plugins', [])])
        added_wn = (new_wn - current_wn) | wn_with_changed_socket
        deleted_wn = current_wn - new_wn - wn_with_changed_socket
        maybechanged_wn = current_wn - deleted_wn
        changed_wn = set([])

        if wn_with_deleted_socket and wn_with_deleted_socket not in new_wn:
            raise ValueError('Watchers %s uses a socket which is deleted' %
                             wn_with_deleted_socket)

        # get changed watchers
        for n in maybechanged_wn:
            w = self.get_watcher(n)
            new_watcher_cfg = (self.get_watcher_config(new_cfg, n) or
                               self.get_plugin_config(new_cfg, n))
            old_watcher_cfg = w._cfg.copy()

            if 'env' in new_watcher_cfg:
                new_watcher_cfg['env'] = parse_env_dict(new_watcher_cfg['env'])

            # discarding env exceptions
            for key in _ENV_EXCEPTIONS:
                if 'env' in new_watcher_cfg and key in new_watcher_cfg['env']:
                    del new_watcher_cfg['env'][key]

                if 'env' in new_watcher_cfg and key in old_watcher_cfg['env']:
                    del old_watcher_cfg['env'][key]

            diff = DictDiffer(new_watcher_cfg, old_watcher_cfg).changed()

            if diff == set(['numprocesses']):
                # if nothing but the number of processes is
                # changed, just changes this
                yield w.set_numprocesses(int(new_watcher_cfg['numprocesses']))
                changed = False
            else:
                changed = len(diff) > 0

            if changed:
                # Others things are changed. Just delete and add the watcher.
                changed_wn.add(n)
                deleted_wn.add(n)
                added_wn.add(n)

        # delete watchers
        for n in deleted_wn:
            w = self.get_watcher(n)
            yield w._stop()
            del self._watchers_names[w.name.lower()]
            self.watchers.remove(w)

        # add watchers
        for n in added_wn:
            new_watcher_cfg = (self.get_plugin_config(new_cfg, n) or
                               self.get_watcher_config(new_cfg, n))

            w = Watcher.load_from_config(new_watcher_cfg)
            w.initialize(self.evpub_socket, self.sockets, self)
            yield self.start_watcher(w)
            self.watchers.append(w)
            self._watchers_names[w.name.lower()] = w

    @classmethod
    def load_from_config(cls, config_file, loop=None):
        cfg = get_config(config_file)
        watchers = []
        for watcher in cfg.get('watchers', []):
            watchers.append(Watcher.load_from_config(watcher))

        sockets = []
        for socket_ in cfg.get('sockets', []):
            sockets.append(CircusSocket.load_from_config(socket_))

        httpd = cfg.get('httpd', False)
        if httpd:
            # controlling that we have what it takes to run the web UI
            # if something is missing this will tell the user
            try:
                import circusweb  # NOQA
            except ImportError:
                logger.error('You need to install circus-web')
                sys.exit(1)

        # creating arbiter
        arbiter = cls(watchers, cfg['endpoint'], cfg['pubsub_endpoint'],
                      check_delay=cfg.get('check_delay', 1.),
                      prereload_fn=cfg.get('prereload_fn'),
                      statsd=cfg.get('statsd', False),
                      stats_endpoint=cfg.get('stats_endpoint'),
                      papa_endpoint=cfg.get('papa_endpoint'),
                      multicast_endpoint=cfg.get('multicast_endpoint'),
                      plugins=cfg.get('plugins'), sockets=sockets,
                      warmup_delay=cfg.get('warmup_delay', 0),
                      httpd=httpd,
                      loop=loop,
                      httpd_host=cfg.get('httpd_host', 'localhost'),
                      httpd_port=cfg.get('httpd_port', 8080),
                      debug=cfg.get('debug', False),
                      debug_gc=cfg.get('debug_gc', False),
                      ssh_server=cfg.get('ssh_server', None),
                      pidfile=cfg.get('pidfile', None),
                      loglevel=cfg.get('loglevel', None),
                      logoutput=cfg.get('logoutput', None),
                      loggerconfig=cfg.get('loggerconfig', None),
                      fqdn_prefix=cfg.get('fqdn_prefix', None),
                      umask=cfg['umask'],
                      endpoint_owner=cfg.get('endpoint_owner', None))

        # store the cfg which will be used, so it can be used later
        # for checking if the cfg has been changed
        arbiter._cfg = cls.get_arbiter_config(cfg)
        arbiter.config_file = config_file

        return arbiter

    def iter_watchers(self, reverse=True):
        return sorted(self.watchers, key=lambda a: a.priority, reverse=reverse)

    @debuglog
    def initialize(self):
        # set process title
        _setproctitle(self.proc_name)

        # set umask even though we may have already set it early in circusd.py
        if self.umask is not None:
            os.umask(self.umask)

        # event pub socket
        self.evpub_socket = self.context.socket(zmq.PUB)
        self.evpub_socket.bind(self.pubsub_endpoint)
        self.evpub_socket.linger = 0

        # initialize sockets
        if len(self.sockets) > 0:
            self.sockets.bind_and_listen_all()
            logger.info("sockets started")

        # initialize watchers
        for watcher in self.iter_watchers():
            self._watchers_names[watcher.name.lower()] = watcher
            watcher.initialize(self.evpub_socket, self.sockets, self)

    @gen.coroutine
    def start_watcher(self, watcher):
        """Aska a specific watcher to start and wait for the specified
        warmup delay."""
        if watcher.autostart:
            yield watcher._start()
            yield tornado_sleep(self.warmup_delay)

    @gen.coroutine
    @debuglog
    def start(self, cb=None):
        """Starts all the watchers.

        If the ioloop has been provided during __init__() call,
        starts all watchers as a standard coroutine

        If the ioloop hasn't been provided during __init__() call (default),
        starts all watchers and the eventloop (and blocks here). In this mode
        the method MUST NOT yield anything because it's called as a standard
        method.

        :param cb: Callback called after all the watchers have been started,
                   when the loop hasn't been provided.
        :type function:
        """
        logger.info("Starting master on pid %s", self.pid)
        self.initialize()

        # start controller
        self.ctrl.start()
        self._restarting = False
        try:
            # initialize processes
            logger.debug('Initializing watchers')
            if self._provided_loop:
                yield self.start_watchers()
            else:
                # start_watchers will be called just after the start_io_loop()
                if not cb:
                    def cb(x): pass
                self.loop.add_future(self.start_watchers(), cb)
            logger.info('Arbiter now waiting for commands')
            self._running = True
            if not self._provided_loop:
                # If an event loop is not provided, block at this line
                self.start_io_loop()
        finally:
            if not self._provided_loop:
                # If an event loop is not provided, do some cleaning
                self.stop_controller_and_close_sockets()
        raise gen.Return(self._restarting)

    def stop_controller_and_close_sockets(self):
        self.ctrl.stop()
        self.evpub_socket.close()

        if len(self.sockets) > 0:
            self.sockets.close_all()

        self._running = False

    def start_io_loop(self):
        """Starts the ioloop and wait inside it
        """
        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
            else:
                break

    @synchronized("arbiter_stop")
    @gen.coroutine
    def stop(self):
        yield self.__stop(True)

    @gen.coroutine
    def _emergency_stop(self):
        """Emergency and fast stop, to use only in circusd
        """
        for watcher in self.iter_watchers():
            watcher.graceful_timeout = 0
        yield self._stop_watchers()
        self.stop_controller_and_close_sockets()

    @gen.coroutine
    def __stop(self, for_shutdown=False):
        logger.info('Arbiter exiting')
        self._stopping = True
        yield self._stop_watchers(close_output_streams=True,
                                  for_shutdown=for_shutdown)
        if self._provided_loop:
            cb = self.stop_controller_and_close_sockets
            self.loop.add_callback(cb)
        else:
            # stop_controller_and_close_sockets will be
            # called in the end of start() method
            self.loop.add_callback(self.loop.stop)

    def reap_processes(self):
        # map watcher to pids
        watchers_pids = {}
        for watcher in self.iter_watchers():
            if not watcher.is_stopped():
                for process in watcher.processes.values():
                    watchers_pids[process.pid] = watcher

        # detect dead children
        if not IS_WINDOWS:
            while True:
                try:
                    # wait for our child (so it's not a zombie)
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if not pid:
                        break

                    if pid in watchers_pids:
                        watcher = watchers_pids[pid]
                        watcher.reap_process(pid, status)
                except OSError as e:
                    if e.errno == errno.ECHILD:
                        # process already reaped
                        return
                    else:
                        raise

    @synchronized("manage_watchers")
    @gen.coroutine
    def manage_watchers(self):
        if self._stopping:
            return

        need_on_demand = False
        # manage and reap processes
        self.reap_processes()
        list_to_yield = []
        for watcher in self.iter_watchers():
            if watcher.on_demand and watcher.is_stopped():
                need_on_demand = True
            list_to_yield.append(watcher.manage_processes())
        if len(list_to_yield) > 0:
            yield list_to_yield

        if need_on_demand:
            sockets = [x.fileno() for x in self.sockets.values()]
            rlist, wlist, xlist = select.select(sockets, [], [], 0)
            if rlist:
                self.socket_event = True
                self._start_watchers()
                self.socket_event = False

    @synchronized("arbiter_reload")
    @gen.coroutine
    @debuglog
    def reload(self, graceful=True, sequential=False):
        """Reloads everything.

        Run the :func:`prereload_fn` callable if any, then gracefuly
        reload all watchers.
        """
        if self._stopping:
            return
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        # reopen log files
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.acquire()
                handler.stream.close()
                handler.stream = open(handler.baseFilename, handler.mode)
                handler.release()

        # gracefully reload watchers
        for watcher in self.iter_watchers():
            yield watcher._reload(graceful=graceful, sequential=sequential)
            tornado_sleep(self.warmup_delay)

    def numprocesses(self):
        """Return the number of processes running across all watchers."""
        return sum([len(watcher) for watcher in self.watchers])

    def numwatchers(self):
        """Return the number of watchers."""
        return len(self.watchers)

    def get_watcher(self, name):
        """Return the watcher *name*."""
        return self._watchers_names[name.lower()]

    def statuses(self):
        return dict([(watcher.name, watcher.status())
                     for watcher in self.watchers])

    @synchronized("arbiter_add_watcher")
    def add_watcher(self, name, cmd, **kw):
        """Adds a watcher.

        Options:

        - **name**: name of the watcher to add
        - **cmd**: command to run.
        - all other options defined in the Watcher constructor.
        """
        if name.lower() in self._watchers_names:
            raise AlreadyExist("%r already exist" % name)

        if not name:
            return ValueError("command name shouldn't be empty")

        watcher = Watcher(name, cmd, **kw)
        if self.evpub_socket is not None:
            watcher.initialize(self.evpub_socket, self.sockets, self)
        self.watchers.append(watcher)
        self._watchers_names[watcher.name.lower()] = watcher
        watcher.notify_event("add", {"time": time.time()})
        return watcher

    @synchronized("arbiter_rm_watcher")
    @gen.coroutine
    def rm_watcher(self, name, nostop=False):
        """Deletes a watcher.

        Options:

        - **name**: name of the watcher to delete
        """
        logger.debug('Deleting %r watcher', name)

        # remove the watcher from the list
        watcher = self._watchers_names.pop(name.lower())
        watcher.notify_event("remove", {"time": time.time()})
        del self.watchers[self.watchers.index(watcher)]

        if not nostop:
            # stop the watcher
            yield watcher._stop()

    @synchronized("arbiter_start_watchers")
    @gen.coroutine
    def start_watchers(self, watcher_iter_func=None):
        yield self._start_watchers(watcher_iter_func=watcher_iter_func)

    @gen.coroutine
    def _start_watchers(self, watcher_iter_func=None):
        if watcher_iter_func is None:
            watchers = self.iter_watchers()
        else:
            watchers = watcher_iter_func()
        for watcher in watchers:
            if watcher.autostart:
                yield watcher._start()
                yield tornado_sleep(self.warmup_delay)

    @gen.coroutine
    @debuglog
    def _stop_watchers(self, close_output_streams=False,
                       watcher_iter_func=None, for_shutdown=False):
        if watcher_iter_func is None:
            watchers = self.iter_watchers(reverse=False)
        else:
            watchers = watcher_iter_func(reverse=False)
        yield [w._stop(close_output_streams, for_shutdown)
               for w in watchers]

    @synchronized("arbiter_stop_watchers")
    @gen.coroutine
    def stop_watchers(self, watcher_iter_func=None):
        yield self._stop_watchers(watcher_iter_func=watcher_iter_func)

    @gen.coroutine
    def _restart(self, inside_circusd=False, watcher_iter_func=None):
        if inside_circusd:
            self._restarting = True
            yield self.__stop()
        else:
            yield self._stop_watchers(watcher_iter_func=watcher_iter_func)
            yield self._start_watchers(watcher_iter_func=watcher_iter_func)

    @synchronized("arbiter_restart")
    @gen.coroutine
    def restart(self, inside_circusd=False, watcher_iter_func=None):
        yield self._restart(inside_circusd=inside_circusd,
                            watcher_iter_func=watcher_iter_func)

    @property
    def endpoint_owner_mode(self):
        return self.ctrl.endpoint_owner_mode  # just wrap the controller


class ThreadedArbiter(Thread, Arbiter):

    def __init__(self, *args, **kw):
        Thread.__init__(self)
        Arbiter.__init__(self, *args, **kw)

    def start(self):
        return Thread.start(self)

    def run(self):
        return Arbiter.start(self)

    def stop(self):
        Arbiter.stop(self)
        if get_ident() != self.ident and self.isAlive():
            self.join()
