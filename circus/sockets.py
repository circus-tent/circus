import socket
import os

from circus import logger
from circus.util import papa


_FAMILY = {
    'AF_INET': socket.AF_INET,
    'AF_INET6': socket.AF_INET6
}

if hasattr(socket, 'AF_UNIX'):
    _FAMILY['AF_UNIX'] = socket.AF_UNIX

_TYPE = {
    'SOCK_STREAM': socket.SOCK_STREAM,
    'SOCK_DGRAM': socket.SOCK_DGRAM,
    'SOCK_RAW': socket.SOCK_RAW,
    'SOCK_RDM': socket.SOCK_RDM,
    'SOCK_SEQPACKET': socket.SOCK_SEQPACKET
}


def addrinfo(host, port, family):
    for _addrinfo in socket.getaddrinfo(host, port):
        if len(_addrinfo[-1]) == 2:
            return _addrinfo[-1][-2], _addrinfo[-1][-1]

        if family == socket.AF_INET6 and len(_addrinfo[-1]) == 4:
            return _addrinfo[-1][-4], _addrinfo[-1][-3]

    raise ValueError((host, port))


class PapaSocketProxy(object):
    def __init__(self, name='', host='localhost', port=8080,
                 family=socket.AF_INET, type=socket.SOCK_STREAM,
                 proto=0, backlog=2048, path=None, umask=None, replace=False,
                 interface=None, so_reuseport=False):
        if path is not None:
            if not hasattr(socket, 'AF_UNIX'):
                raise NotImplementedError("AF_UNIX not supported on this"
                                          " platform")
            else:
                family = socket.AF_UNIX

        with papa.Papa() as p:
            papa_socket = p.make_socket('circus.' + name, host, port, family, type, backlog, path, umask, interface, so_reuseport)

        self.name = name
        self.host = papa_socket.get('host')
        self.port = papa_socket.get('port')
        self.family = papa_socket['family']
        self.socktype = papa_socket['type']
        self.backlog = papa_socket.get('backlog')
        self.path = papa_socket.get('path')
        self.umask = papa_socket.get('umask')
        self.interface = papa_socket.get('interface')
        self.so_reuseport = papa_socket.get('so_reuseport', False)
        self._fileno = papa_socket.get('fileno')

        self.replace = True

    def fileno(self):
        return self._fileno

    @property
    def location(self):
        if self.path:
            return '%r' % self.path
        return '%s:%d' % (self.host, self.port)

    def __str__(self):
        return 'socket %r at %s' % (self.name, self.location)

    def close(self):
        pass  # papa manages the lifetime of these

    def bind_and_listen(self):
        pass  # handled by papa


class CircusSocket(socket.socket):
    """Inherits from socket, to add a few extra options.
    """
    def __init__(self, name='', host='localhost', port=8080,
                 family=socket.AF_INET, type=socket.SOCK_STREAM,
                 proto=0, backlog=2048, path=None, umask=None, replace=False,
                 interface=None, so_reuseport=False):
        if path is not None:
            if not hasattr(socket, 'AF_UNIX'):
                raise NotImplementedError("AF_UNIX not supported on this"
                                          " platform")
            else:
                family = socket.AF_UNIX

        super(CircusSocket, self).__init__(family=family, type=type,
                                           proto=proto)
        self.name = name
        self.socktype = type
        self.path = path
        self.umask = umask
        self.replace = replace

        if hasattr(socket, 'AF_UNIX') and family == socket.AF_UNIX:
            self.host = self.port = None
            self.is_unix = True
        else:
            self.host, self.port = addrinfo(host, port, family)
            self.is_unix = False

        self.interface = interface
        self.backlog = backlog
        self.so_reuseport = so_reuseport

        if self.so_reuseport and hasattr(socket, 'SO_REUSEPORT'):
            try:
                self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except socket.error:
                # see 699
                pass
        else:
            self.so_reuseport = False

        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Since python 3.4, file descriptors inheritance for children processes
        #  is not the default anymore (#787)
        if hasattr(self, 'set_inheritable'):
            self.set_inheritable(True)

    @property
    def location(self):
        if self.is_unix:
            return '%r' % self.path
        return '%s:%d' % (self.host, self.port)

    def __str__(self):
        return 'socket %r at %s' % (self.name, self.location)

    def close(self):
        socket.socket.close(self)
        if self.is_unix and os.path.exists(self.path):
            os.remove(self.path)

    def bind_and_listen(self):
        try:
            if self.is_unix:
                if os.path.exists(self.path):
                    if self.replace:
                        os.unlink(self.path)
                    else:
                        raise OSError("%r already exists. You might want to "
                                      "remove it. If it's a stalled socket "
                                      "file, just restart Circus" % self.path)
                if self.umask is None:
                    self.bind(self.path)
                else:
                    old_mask = os.umask(self.umask)
                    self.bind(self.path)
                    os.umask(old_mask)
            else:
                if self.interface is not None:
                    # Bind to device if given, e.g. to limit which device to
                    # bind when binding on IN_ADDR_ANY or IN_ADDR_BROADCAST.
                    import IN
                    if hasattr(IN, 'SO_BINDTODEVICE'):
                        self.setsockopt(socket.SOL_SOCKET, IN.SO_BINDTODEVICE,
                                        self.interface + '\0')
                        logger.debug('Binding to device: %s' % self.interface)

                self.bind((self.host, self.port))
        except socket.error:
            logger.error('Could not bind %s' % self.location)
            raise

        self.setblocking(0)
        if self.socktype in (socket.SOCK_STREAM, socket.SOCK_SEQPACKET):
            self.listen(self.backlog)

        if not self.is_unix:
            if self.family == socket.AF_INET6:
                self.host, self.port, _flowinfo, _scopeid = self.getsockname()
            else:
                self.host, self.port = self.getsockname()

        logger.debug('Socket bound at %s - fd: %d' % (self.location,
                                                      self.fileno()))

    @classmethod
    def load_from_config(cls, config):
        if (config.get('family') == 'AF_UNIX' and
                not hasattr(socket, 'AF_UNIX')):
            raise NotImplementedError("AF_UNIX not supported on this"
                                      "platform")

        params = {'name': config['name'],
                  'host': config.get('host', 'localhost'),
                  'port': int(config.get('port', '8080')),
                  'path': config.get('path'),
                  'interface': config.get('interface', None),
                  'family': _FAMILY[config.get('family', 'AF_INET').upper()],
                  'type': _TYPE[config.get('type', 'SOCK_STREAM').upper()],
                  'backlog': int(config.get('backlog', 2048)),
                  'so_reuseport': config.get('so_reuseport', False),
                  'umask': int(config.get('umask', 8)),
                  'replace': config.get('replace')}
        use_papa = config.get('use_papa', False) and papa is not None
        proto_name = config.get('proto')
        if proto_name is not None:
            params['proto'] = socket.getprotobyname(proto_name)
        socket_class = PapaSocketProxy if use_papa else cls
        s = socket_class(**params)

        # store the config for later checking if config has changed
        s._cfg = config.copy()

        return s


class CircusSockets(dict):
    """Manage CircusSockets objects.
    """
    def __init__(self, sockets=None, backlog=2048):
        super(CircusSockets, self).__init__()
        self.backlog = backlog
        if sockets is not None:
            for sock in sockets:
                self[sock.name] = sock

    def add(self, name, host='localhost', port=8080, family=socket.AF_INET,
            type=socket.SOCK_STREAM, proto=0, backlog=None, path=None,
            umask=None, interface=None, use_papa=False):

        if backlog is None:
            backlog = self.backlog

        sock = self.get(name)
        if sock is not None:
            raise ValueError('A socket already exists %s' % sock)

        socket_class = PapaSocketProxy if use_papa else CircusSocket
        sock = socket_class(name=name, host=host, port=port, family=family,
                            type=type, proto=proto, backlog=backlog, path=path,
                            umask=umask, interface=interface)
        self[name] = sock
        return sock

    def close_all(self):
        for sock in self.values():
            sock.close()

    def bind_and_listen_all(self):
        for sock in self.values():
            # so_reuseport sockets should not be bound at this point
            if not sock.so_reuseport:
                sock.bind_and_listen()
