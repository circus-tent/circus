import json
import socket
from urlparse import urlparse


class AutoDiscovery(object):

    def __init__(self, multicast_endpoint, loop, nodes,
                 discovery_callback):
        """
        :param nodes: The list of nodes to send via UDP broadcast.
        :param discovery_callback: callabck called when a new node is detected
                                  on the cluster.
        """
        self.loop = loop
        self.discovery_callback = discovery_callback

        parsed = urlparse(multicast_endpoint).netloc.split(':')
        addr = parsed[0], int(parsed[1])

        self.sock = create_udp_socket(*addr)

        self.loop.add_handler(self.sock.fileno(), self.get_message,
                              self.loop.READ)
        # Send an UDP broadcast message to everyone, with our info.
        self.send_message(addr, nodes=nodes, data_type='hey')

    def send_message(self, addr, nodes, data_type):
        payload = json.dumps({'type': data_type, 'nodes': nodes})
        self.sock.sendto(payload, addr)

    def get_message(self, fd_no, type):
        data, emitter_addr = self.sock.recvfrom(1024)

        try:
            self.discovery_callback(json.loads(data), emitter_addr,
                                    self.send_message)
        except ValueError:
            self.log.warning('Unable to parse the message received from the '
                             'UDP socket')


def create_udp_socket(multicast_addr, multicast_port, any_addr='0.0.0.0'):
    any_addr = '0.0.0.0'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                         socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if hasattr(socket, 'SO_REUSEPORT'):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                    (socket.inet_aton(multicast_addr)
                     + socket.inet_aton(any_addr)))
    sock.bind((any_addr, multicast_port))
    return sock
