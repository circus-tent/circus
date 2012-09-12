import socket
from circus import logger


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
    for _addrinfo in socket.getaddrinfo(host, port):
        if len(_addrinfo[-1]) == 2:
            return _addrinfo[-1][-2], _addrinfo[-1][-1]

    raise ValueError((host, port))


class CircusSocket(socket.socket):
    """Inherits from socket, to add a few extra options.
    """
    def __init__(self, name='', host='localhost', port=8080,
                 family=socket.AF_INET, type=socket.SOCK_STREAM,
                 proto=0, backlog=2048):
        super(CircusSocket, self).__init__(family=family, type=type,
                                           proto=proto)
        self.name = name
        self.socktype = type
        self.host, self.port = addrinfo(host, port)
        self.backlog = backlog
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __str__(self):
        return 'socket %r at %s:%d' % (self.name, self.host, self.port)

    def bind_and_listen(self):
        try:
            self.bind((self.host, self.port))
        except socket.error:
            logger.error('Could not bind %s:%d' % (self.host, self.port))
            raise

        self.setblocking(0)
        if self.socktype in (socket.SOCK_STREAM, socket.SOCK_SEQPACKET):
            self.listen(self.backlog)
        self.host, self.port = self.getsockname()
        logger.debug('Socket bound at %s:%d - fd: %d' % (self.host, self.port,
                                                         self.fileno()))

    @classmethod
    def load_from_config(cls, config):
        params = {'name': config['name'],
                  'host': config.get('host', 'localhost'),
                  'port': int(config.get('port', '8080')),
                  'family': _FAMILY[config.get('family', 'AF_INET').upper()],
                  'type': _TYPE[config.get('type', 'SOCK_STREAM').upper()],
                  'backlog': int(config.get('backlog', 2048))}
        proto_name = config.get('proto')
        if proto_name is not None:
            params['proto'] = socket.getprotobyname(proto_name)
        return cls(**params)


class CircusSockets(dict):
    """Manage CircusSockets objects.
    """
    def __init__(self, sockets=None, backlog=2048):
        self.backlog = backlog
        if sockets is not None:
            for sock in sockets:
                self[sock.name] = sock

    def add(self, name, host='localhost', port=8080, family=socket.AF_INET,
            type=socket.SOCK_STREAM, proto=0, backlog=None):

        if backlog is None:
            backlog = self.backlog

        sock = self.get(name)
        if sock is not None:
            raise ValueError('A socket already exists %s' % sock)

        sock = CircusSocket(name, host, port, family, type, proto, backlog)
        self[name] = sock
        return sock

    def close_all(self):
        for sock in self.values():
            sock.close()

    def bind_and_listen_all(self):
        for sock in self.values():
            sock.bind_and_listen()
