import socket


_FAMILY = {
    'AF_UNIX': socket.AF_UNIX,
    'AF_INET': socket.AF_INET,
    'AF_INET6': socket.AF_INET6
}

_TYPE = {
    'SOCK_STREAM': socket.SOCK_STREAM,
    'SOCK_DGRAM': socket.SOCK_DGRAM,
    'SOCK_RAW': socket.SOCK_RAW,
    'SOCK_RDM': socket.SOCK_RDM,
    'SOCK_SEQPACKET': socket.SOCK_SEQPACKET
}


def addrinfo(host, port):
    return socket.getaddrinfo(host, port)[0][-1]


class CircusSocket(object):
    """Wraps a socket object.
    """
    def __init__(self, host='localhost', port=8080, family=socket.AF_INET,
                 type=socket.SOCK_STREAM):
        # creating a socket
        self.sock = socket.socket(family, type)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host, self.port = addrinfo(host, port)

    @property
    def name(self):
        return self.sock.getsockname()

    @property
    def fileno(self):
        return self.sock.fileno()

    @classmethod
    def from_config(cls, config):
        host = config.get('host', 'localhost')
        port = int(config.get('port', '8080'))
        family = _FAMILY[config.get('family', 'AF_INET').upper()]
        type = _TYPE[config.get('type', 'SOCK_STREAM').upper()]
        return cls(host, port, family, type)

    def bind_and_listen(self, backlog=1):
        self.sock.bind((self.host, self.port))
        self.sock.listen(backlog)

    def close(self):
        return self.sock.close()


class CircusSocketManager(object):
    """Manage CircusSockets objects.
    """
    def __init__(self, backlog=1, sockets=None):
        self.backlog = backlog
        self._mrk = 0
        if sockets is None:
            self.sockets = {}
        else:
            for sock in sockets:
                self._add(sock)

    @property
    def names(self):
        names = []
        for host, port, marker in self.sockets:
            names.append((host, port))
        names.sort()
        return names

    def _incr_marker(self):
        self._mrk += 1
        return self._mrk

    def _add(self, sock):
        host, port = sock.name
        if port == 0:
            marker = self._incr_marker()
        else:
            marker = -1
        self.sockets[host, port, marker] = sock

    def _get(self, host, port):
        host, port = addrinfo(host, port)

        if port != 0:
            return [self.sockets[host, port, -1]]

        res = []
        for (_host, _port, marker), sock in self.sockets.items():
            if host == _host and _port == 0:
                res.append(sock)

        return res

    def _del(self, host, port):
        host, port = addrinfo(host, port)

        if port != 0:
            socket = self.sockets[host, port, -1]
            socket.close()
            del self.sockets[host, port, -1]
        else:
            removed = 0
            for (_host, _port, marker), sock in self.sockets.items():
                if host == _host and _port == 0:
                    sock.close()
                    del self.sockets[host, 0, marker]
                    removed += 1
            if removed == 0:
                raise KeyError((host, port))

    def add(self, host='localhost', port=8080, family=socket.AF_INET,
            type=socket.SOCK_STREAM):
        host, port = addrinfo(host, port)
        if (host, port, -1) in self.sockets and port != 0:
            raise ValueError('A socket already exists on %s:%d' % (host, port))
        sock = CircusSocket(host, port, family, type)
        self._add(sock)
        return sock

    def remove(self, host, port):
        self._del(host, port)

    def _resync(self):
        for (_host, _port, marker), sock in self.sockets.items():
            host, port = sock.name
            if host != _host or port != _port:
                del self.sockets[_host, _port, marker]
                if port == 0:
                    marker = self._incr_mrk()
                else:
                    marker = -1
                self.sockets[host, port, marker] = sock

    def bind_and_listen_all(self):
        for sock in self.sockets.values():
            sock.bind_and_listen(self.backlog)
        self._resync()

    def bind_and_listen(self, host, port):
        for sock in self._get(host, port):
            sock.bind_and_listen(self.backlog)
        self._resync()

    def get_fileno(self, host, port):
        for sock in self._get(host, port):
            yield sock.fileno

    def close_all(self):
        for sock in self.sockets.values():
            sock.close()

    def close(self, host, port):
        for sock in self._get(host, port):
            sock.close()
