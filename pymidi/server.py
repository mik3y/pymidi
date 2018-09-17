from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from optparse import OptionParser
import logging
import select
import socket
import sys

from pymidi.protocol import DataProtocol
from pymidi.protocol import ControlProtocol

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

logger = logging.getLogger('pymidi.server')

parser = OptionParser()
parser.add_option('-p', '--port',
    type='int',
    dest='port',
    default=5051,
    help='server command port; port + 1 will also be used')
parser.add_option('-b', '--bind_host',
    dest='host',
    default='0.0.0.0',
    help='bind to this address')
parser.add_option('-v', '--verbose',
    action='store_true',
    dest='verbose',
    default=False,
    help='show verbose logs')


class Handler(object):
    def on_peer_connected(self, peer):
        pass

    def on_peer_disconnected(self, peer):
        pass

    def on_midi_commands(self, peer, command_list):
        pass


class Server(object):
    def __init__(self, host='0.0.0.0', port=5051):
        self.host = host
        self.port = port
        self.handlers = set()

    def add_handler(self, handler):
        assert isinstance(handler, Handler)
        self.handlers.add(handler)

    def remove_handler(self, handler):
        assert isinstance(handler, Handler)
        self.handlers.discard(handler)

    def _peer_connected_cb(self, peer):
        for handler in self.handlers:
            handler.on_peer_connected(peer)

    def _peer_disconnected_cb(self, peer):
        for handler in self.handlers:
            handler.on_peer_disconnected(peer)

    def _midi_command_cb(self, peer, midi_packet):
        commands = midi_packet.command.midi_list
        for handler in self.handlers:
            handler.on_midi_commands(peer, commands)

    def serve_forever(self):
        control_port, data_port = self.port, self.port + 1
        logger.info('Control socket on {}:{}'.format(self.host, control_port))
        control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        control_socket.bind((self.host, control_port))

        logger.info('Data socket on {}:{}'.format(self.host, data_port))
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_socket.bind((self.host, data_port))

        data_protocol = DataProtocol(data_socket, midi_command_cb=self._midi_command_cb)
        control_protocol = ControlProtocol(
            data_protocol,
            control_socket,
            connect_cb=self._peer_connected_cb,
            disconnect_cb=self._peer_disconnected_cb)

        while True:
            rr, _, _ = select.select([control_socket, data_socket], [], [])
            for s in rr:
                buffer, addr = s.recvfrom(1024)
                if s is control_socket:
                    control_protocol.handle_message(buffer, addr)
                elif s is data_socket:
                    data_protocol.handle_message(buffer, addr)
                else:
                    raise ValueError('Unknown socket.')


if __name__ == '__main__':
    options, args = parser.parse_args()

    log_level = logging.DEBUG if options.verbose else logging.INFO
    if coloredlogs:
        coloredlogs.install(level=log_level)
    else:
        logging.basicConfig(level=log_level)

    class ExampleHandler(Handler):
        """Example handler.

        This handler doesn't do all that much; we're just using one here to
        illustrate the handler interface, so you can write a much cooler one.
        """
        def __init__(self):
            self.logger = logging.getLogger('ExampleHandler')

        def on_peer_connected(self, peer):
            self.logger.info('Peer connected: {}'.format(peer))

        def on_peer_disconnected(self, peer):
            self.logger.info('Peer disconnected: {}'.format(peer))

        def on_midi_commands(self, peer, command_list):
            for command in command_list:
                if command.command == 'note_on':
                    key = command.params.key
                    velocity = command.params.velocity
                    print('Someone hit the key {} with velocity {}'.format(key, velocity))

    server = Server(port=options.port, host=options.host)
    server.add_handler(ExampleHandler())

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Got CTRL-C, quitting')
        sys.exit(0)
