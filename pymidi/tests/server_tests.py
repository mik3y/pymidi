from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from unittest import TestCase
from pymidi.server import Server, Handler
import mock


class FakeHandler(mock.Mock, Handler):
    pass


class ServerTests(TestCase):
    def setUp(self):
        self.server = Server([('127.0.0.1', 0)])
        self.server._init_protocols()
        self.handler = FakeHandler()
        self.server.add_handler(self.handler)

    def test_server_bind(self):
        protos = self.server.socket_map
        self.assertEqual(2, len(protos))

    def test_loop_once_no_data(self):
        """Confirms a single read loop succeeds with no data."""
        self.server._loop_once(timeout=0)
        self.assertFalse(self.handler.called)
        self.assertEqual(0, self.handler.call_count)
