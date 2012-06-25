from threading import Thread
import time
import socket
import os

from circus.stats.collector import SocketStatsCollector
from circus.tests.support import unittest

from zmq.eventloop import ioloop


TRAVIS = os.getenv('TRAVIS', False)


class TestSocketCollector(unittest.TestCase):

    def test_socketstats(self):
        if TRAVIS:
            return

        # let's create 10 sockets and their clients
        socks = []
        clients = []
        fds = []

        for i in range(10):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', 0))
            sock.listen(1)
            socks.append((sock, 'localhost:0'))
            fds.append(sock.fileno())
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(sock.getsockname())
            clients.append(client)

        class FakeStreamer(object):
            stats = []

            @property
            def publisher(self):
                return self

            def get_sockets(self):
                return socks

            def publish(self, name, stat):
                self.stats.append(stat)

        streamer = FakeStreamer()

        # now the stats collector
        class Collector(Thread):

            def __init__(self, streamer):
                Thread.__init__(self)
                self.streamer = streamer
                self.loop = ioloop.IOLoop.instance()
                self.daemon = True

            def run(self):
                collector = SocketStatsCollector(streamer, 'sockets',
                                                 callback_time=0.1,
                                                 io_loop=self.loop)
                collector.start()
                self.loop.start()

            def stop(self):
                self.loop.stop()

        collector = Collector(streamer)
        collector.start()
        time.sleep(1.)

        # doing some socket things as a client
        for i in range(10):
            for client in clients:
                client.send('ok')
                #client.recv(2)

        # stopping
        collector.stop()
        for s, _ in socks:
            s.close()

        # let's see what we got
        self.assertTrue(len(streamer.stats) > 2)

        stat = streamer.stats[0]
        self.assertTrue(stat['fd'] in fds)
        self.assertTrue(stat['reads'] > 10.)
