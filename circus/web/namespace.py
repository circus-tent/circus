from socketio.mixins import RoomsMixin, BroadcastMixin
from socketio.namespace import BaseNamespace

from circus.stats.client import StatsClient
from circus.web.session import get_client


class StatsNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):

    def __init__(self, *args, **kwargs):
        super(StatsNamespace, self).__init__(*args, **kwargs)
        self._running = True

    def on_get_stats(self, msg):
        """This method is the one way to start a conversation with the socket.
        When sending a message here, the parameters are packt into the msg
        dictionary, which contains:

            - "streams", a list of streams that the client want to be notified
              about.
            - "get_processes", if it wants to include the subprocesses managed
              by this watcher or not (optional, defaults to False)

        The server sends back to the client some messages, on different
        channels:

            - "stats-<watchername>" sends memory and cpu info for the
              aggregation of stats.
            - stats-<watchername>-pids sends the list of pids for this watcher
            - "stats-<watchername>-<pid>" sends the information about
              specific pids for the different watchers (works only if
              "get_processes" is set to True when calling this method)
            - "socket-stats" send the aggregation information about
               sockets.
            - "socket-stats-<fd>" sends information about a particular fd.
        """

        # unpack the params
        streams = msg.get('watchers', [])
        streams_with_pids = msg.get('watchersWithPids', [])

        # if we want to supervise the processes of a watcher, then send the
        # list of pids trough a socket. If we asked about sockets, do the same
        # with their fds
        client = get_client()
        for watcher in streams_with_pids:
            if watcher == "sockets":
                fds = [s['fd'] for s in client.get_sockets()]
                self.send_data('socket-stats-fds', fds=fds)
            else:
                pids = [int(pid) for pid in client.get_pids(watcher)]
                channel = 'stats-{watcher}-pids'.format(watcher=watcher)
                self.send_data(channel, pids=pids)

        # Get the channels that are interesting to us and send back information
        # there when we got them.
        stats = StatsClient(endpoint=client.stats_endpoint)
        for watcher, pid, stat in stats:
            if not self._running:
                return

            if watcher == 'sockets':
                # if we get information about sockets and we explicitely
                # requested them, send back the information.
                if 'sockets' in streams_with_pids and 'fd' in stat:
                    self.send_data('socket-stats-{fd}'.format(fd=stat['fd']),
                                   **stat)
                elif 'sockets' in streams and 'addresses' in stat:
                    self.send_data('socket-stats', reads=stat['reads'],
                                   adresses=stat['addresses'])
            else:
                available_watchers = streams + streams_with_pids + ['circus']
                # these are not sockets but normal watchers
                if watcher in available_watchers:
                    if (watcher == 'circus'
                            and stat.get('name', None) in available_watchers):
                        self.send_data(
                            'stats-{watcher}'.format(watcher=stat['name']),
                            mem=stat['mem'], cpu=stat['cpu'], age=stat['age'])
                    else:
                        if pid is None:  # means that it's the aggregation
                            self.send_data(
                                'stats-{watcher}'.format(watcher=watcher),
                                mem=stat['mem'], cpu=stat['cpu'],
                                age=stat['age'])
                        else:
                            if watcher in streams_with_pids:
                                self.send_data(
                                    'stats-{watcher}-{pid}'.format(
                                        watcher=watcher, pid=pid),
                                    mem=stat['mem'],
                                    cpu=stat['cpu'],
                                    age=stat['age'])

    def send_data(self, topic, **kwargs):
        """Send the given dict encoded into json to the listening socket on the
        browser side.

        :param topic: the topic to send the information to
        :param **kwargs: the dict to serialize and send
        """
        pkt = dict(type="event", name=topic, args=kwargs,
                   endpoint=self.ns_name)
        self.socket.send_packet(pkt)

    def recv_disconnect(self):
        """When we receive a disconnect from the client, we want to make sure
        that we close the socket we just opened at the begining of the stat
        exchange."""
        self._running = False
