import re
import socket
import time

from tornado import ioloop
from circus.plugins import CircusPlugin
from circus import logger
from circus import util


class WatchDog(CircusPlugin):
    """Plugin that bind an udp socket and wait for watchdog messages.
    For "watchdoged" processes, the watchdog will kill them (using the "kill"
    command) if they don't send heartbeat in a certain period of time
    materialized by loop_rate * max_count. (circus will automatically restart
    the missing processes in the watcher)

    Each monitored process should send udp message at least at the loop_rate.
    The udp message format is a line of text, decoded using **msg_regex**
    parameter.
    The heartbeat message MUST at least contain the pid of the process sending
    the message.

    The list of monitored watchers are determined by the parameter
    **watchers_regex** in the configuration.

    At startup, the plugin does not know all the circus watchers and pids,
    so it's needed to discover all watchers and pids. After the discover, the
    monitoring list is updated by messages from circusd handled in
    self.handle_recv

    Plugin Options --

    - **loop_rate** -- watchdog loop rate in seconds. At each loop, WatchDog
      will looks for "dead" processes.
    - **watchers_regex** -- regex for matching watcher names that should be
      monitored by the watchdog (default: ".*" all watchers are monitored)
    - **msg_regex** -- regex for decoding the received heartbeat
      message in udp (default: "^(?P<pid>.*);(?P<timestamp>.*)$")
      the default format is a simple text message: "pid;timestamp"
    - **max_count** -- max number of passed loop without receiving
      any heartbeat before restarting process (default: 3)
    - **ip** -- ip the watchdog will bind on (default: 127.0.0.1)
    - **port** -- port the watchdog will bind on (default: 1664)
    - **watchers_stop_signal** -- optionally override the stop_signal used
      when killing the processes
    - **watchers_graceful_timeout** -- optionally override the graceful_timeout
      used when killing the processes
    """
    name = 'watchdog'

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(WatchDog, self).__init__(endpoint, pubsub_endpoint,
                                       check_delay, ssh_server=ssh_server)

        self.loop_rate = float(config.get("loop_rate", 60))  # in seconds
        self.watchers_regex = config.get("watchers_regex", ".*")
        self.msg_regex = config.get("msg_regex",
                                    "^(?P<pid>.*);(?P<timestamp>.*)$")
        self.max_count = int(config.get("max_count", 3))
        self.watchdog_ip = config.get("ip", "127.0.0.1")
        self.watchdog_port = int(config.get("port", 1664))
        self.stop_signal = config.get("watchers_stop_signal")
        if self.stop_signal:
            self.stop_signal = util.to_signum(self.stop_signal)
        self.graceful_timeout = config.get("watchers_graceful_timeout")
        if self.graceful_timeout:
            self.graceful_timeout = float(self.graceful_timeout)

        self.pid_status = dict()
        self.period = None
        self.starting = True

    def handle_init(self):
        """Initialization of plugin

        - set the periodic call back for the process monitoring (at loop_rate)
        - create the listening UDP socket
        """
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000)
        self.period.start()
        self._bind_socket()

    def handle_stop(self):
        if self.period is not None:
            self.period.stop()
        self.sock.close()
        self.sock = None

    def handle_recv(self, data):
        """Handle received message from circusd

        We need to handle two messages:
        - spawn: add a new monitored child pid
        - reap: remove a killed child pid from monitoring
        """
        watcher_name, action, msg = self.split_data(data)
        logger.debug("received data from circusd: watcher.%s.%s, %s",
                     watcher_name, action, msg)
        # check if monitored watchers:
        if self._match_watcher_name(watcher_name):
            try:
                message = self.load_message(msg)
            except ValueError:
                logger.error("Error while decoding json for message: %s",
                             msg)
            else:
                if "process_pid" not in message:
                    logger.warning('no process_pid in message')
                    return
                pid = str(message.get("process_pid"))
                if action == "spawn":
                    self.pid_status[pid] = dict(watcher=watcher_name,
                                                last_activity=time.time())
                    logger.info("added new monitored pid for %s:%s",
                                watcher_name,
                                pid)
                # very questionable fix for Py3 here!
                # had to add check for pid in self.pid_status
                elif action == "reap" and pid in self.pid_status:
                    old_pid = self.pid_status.pop(pid)
                    logger.info("removed monitored pid for %s:%s",
                                old_pid['watcher'],
                                pid)

    def _discover_monitored_pids(self):
        """Try to discover all the monitored pids.

        This should be done only at startup time, because if new watchers or
        pids are created in running time, we should receive the message
        from circusd which is handled by self.handle_recv
        """
        self.pid_status = dict()
        all_watchers = self.call("list")
        for watcher_name in all_watchers['watchers']:
            if self._match_watcher_name(watcher_name):
                processes = self.call("list", name=watcher_name)
                if 'pids' in processes:
                    for pid in processes['pids']:
                        pid = str(pid)
                        self.pid_status[pid] = dict(watcher=watcher_name,
                                                    last_activity=time.time())
                        logger.info("discovered: %s, pid:%s",
                                    watcher_name,
                                    pid)

    def _bind_socket(self):
        """bind the listening socket for watchdog udp and start an event
        handler for handling udp received messages.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((self.watchdog_ip, self.watchdog_port))
        except socket.error as socket_error:
            logger.error(
                "Problem while binding watchdog socket on %s:%s (err %s",
                self.watchdog_ip,
                self.watchdog_port,
                str(socket_error))
            self.sock = None
        else:
            self.sock.settimeout(1)
            self.loop.add_handler(self.sock.fileno(),
                                  self.receive_udp_socket,
                                  ioloop.IOLoop.READ)
            logger.info("Watchdog listening UDP on %s:%s",
                        self.watchdog_ip, self.watchdog_port)

    def _match_watcher_name(self, name):
        """Match the given watcher name with the watcher_regex given in config

        :return: re.match object or None
        """
        return re.match(self.watchers_regex, name)

    def _decode_received_udp_message(self, data):
        """decode the received message according to the msg_regex

        :return: decoded message
        :rtype: dict or None
        """
        result = re.match(self.msg_regex, data)
        if result is not None:
            return result.groupdict()

    def receive_udp_socket(self, fd, events):
        """Check the socket for received UDP message.
        This method is periodically called by the ioloop.
        If messages are received and parsed, update the status of
        the corresponing pid.
        """
        data, _ = self.sock.recvfrom(1024)
        heartbeat = self._decode_received_udp_message(data)
        if "pid" in heartbeat:
            if heartbeat['pid'] in self.pid_status:
                # TODO: check and compare received time
                # with our own time.time()
                self.pid_status[heartbeat["pid"]][
                    'last_activity'] = time.time()
            else:
                logger.warning("received watchdog for a"
                               "non monitored process:%s",
                               heartbeat)
        logger.debug("watchdog message: %s", heartbeat)

    def look_after(self):
        """Checks for the watchdoged watchers and restart a process if no
        received watchdog after the loop_rate * max_count period.
        """
        # if first check, do a full discovery first.
        if self.starting:
            self._discover_monitored_pids()
            self.starting = False

        max_timeout = self.loop_rate * self.max_count
        too_old_time = time.time() - max_timeout
        for pid, detail in self.pid_status.items():
            if detail['last_activity'] < too_old_time:
                logger.info("watcher:%s, pid:%s is not responding. Kill it !",
                            detail['watcher'],
                            pid)

                props = dict(name=detail['watcher'], pid=int(pid))
                if self.stop_signal is not None:
                    props['signum'] = self.stop_signal
                if self.graceful_timeout is not None:
                    props['graceful_timeout'] = self.graceful_timeout

                self.cast('kill', **props)

                # Trusting watcher to eventually stop the process after
                # graceful timeout
                del self.pid_status[pid]
