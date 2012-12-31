import socket
from bottle import ServerAdapter


class SocketIOServer(ServerAdapter):
    def __init__(self, host='127.0.0.1', port=8080, **config):
        super(SocketIOServer, self).__init__(host, port, **config)
        self.fd = config.get('fd')
        if self.fd is not None:
            self.fd = int(self.fd)

    def run(self, handler):
        try:
            from socketio.server import SocketIOServer
        except ImportError:
            raise ImportError('You need to install gevent_socketio')

        # sets up the ZMQ/Gevent environ
        from circus import _patch   # NOQA

        namespace = self.options.get('namespace', 'socket.io')
        policy_server = self.options.get('policy_server', False)

        if self.fd is not None:
            sock = socket.fromfd(self.fd, socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = (self.host, self.port)

        socket_server = SocketIOServer(sock, handler,
                                       namespace=namespace,
                                       policy_server=policy_server)
        handler.socket_server = socket_server
        socket_server.serve_forever()
