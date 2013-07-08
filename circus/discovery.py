import json
import socket
from urlparse import urlparse


class AutoDiscovery(object):

    def __init__(self, multicast_endpoint, loop, discovery_payload,
                 discovery_callback):
        """
        :param discovery_payload: the payload that's sent to the other machines
                                  via the UDP broadcast.
        :param discovery_callback: callabck called when a new node is detected
                                  on the cluster.
        """
        self.loop = loop
        self.discovery_payload = discovery_payload
        self.discovery_callback = discovery_callback

        parsed = urlparse(multicast_endpoint).netloc.split(':')
        self.multicast_addr, self.multicast_port = parsed[0], int(parsed[1])

        self.sock = create_udp_socket(self.multicast_addr, self.multicast_port)

        self.loop.add_handler(self.sock.fileno(), self.get_message,
                              self.loop.READ)
        self.discover()

    def discover(self):
        payload = json.dumps({'type': 'new-node',
                              'data': self.discovery_payload})
        self.sock.sendto(payload, (self.multicast_addr, self.multicast_port))

    def get_message(self, fd_no, type):
        data, address = self.sock.recvfrom(1024)
        try:
            data = json.loads(data)
        except ValueError:
            self.log.warning('Unable to parse the message received from the '
                             'UDP socket')

        if data.get('type') == 'new-node':
            known_node = self.discovery_callback(data['data'])

            if not known_node:
                self.send_message(address)


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
