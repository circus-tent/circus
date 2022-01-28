from unittest import mock

import zmq
import zmq.utils.jsonapi as json

from circus.tests.support import TestCase, EasyTestSuite
from circus.stats.publisher import StatsPublisher


class TestStatsPublisher(TestCase):
    def setUp(self):
        self.publisher = StatsPublisher()
        self.origin_socket = self.publisher.socket
        self.publisher.socket = mock.MagicMock()

    def tearDown(self):
        self.publisher.socket = self.origin_socket
        self.publisher.stop()
        del self.origin_socket

    def test_publish(self):
        stat = {'subtopic': 1, 'foo': 'bar'}
        self.publisher.publish('foobar', stat)
        self.publisher.socket.send_multipart.assert_called_with(
            [b'stat.foobar.1', json.dumps(stat)])

    def test_publish_reraise_zmq_errors(self):
        self.publisher.socket.closed = False
        self.publisher.socket.send_multipart.side_effect = zmq.ZMQError()

        stat = {'subtopic': 1, 'foo': 'bar'}
        self.assertRaises(zmq.ZMQError, self.publisher.publish, 'foobar', stat)

    def test_publish_silent_zmq_errors_when_socket_closed(self):
        self.publisher.socket.closed = True
        self.publisher.socket.send_multipart.side_effect = zmq.ZMQError()

        stat = {'subtopic': 1, 'foo': 'bar'}
        self.publisher.publish('foobar', stat)


test_suite = EasyTestSuite(__name__)
