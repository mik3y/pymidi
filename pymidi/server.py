from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes

from optparse import OptionParser
import logging
import select
import socket
import sys

from pymidi.protocol import DataProtocol
from pymidi.protocol import ControlProtocol
from pymidi import utils

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

logger = logging.getLogger('pymidi.server')

DEFAULT_BIND_ADDR = '0.0.0.0:5051'

parser = OptionParser()
parser.add_option('-b', '--bind_addr',
    dest='bind_addrs',
    action='append',
    default=None,
    help='<ip>:<port> for listening; may give multiple times; default {}'.format(DEFAULT_BIND_ADDR))
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
    def __init__(self, bind_addrs):
        """Creates a new Server instance.

        `bind_addrs` should be an iterable of 1 or more addresses to bind to,
        each a 2-tuple of (ip, port). Socket family will be automatically
        detected from the IP address.
        """
        if not bind_addrs:
            raise ValueError('Must provide at least one bind address.')
        map(utils.validate_addr, bind_addrs)
        self.bind_addrs = bind_addrs
        self.handlers = set()

        # Maps sockets to their protocol handlers.
        self.socket_map = {}

    @classmethod
    def from_bind_addrs(cls, hosts):
        """Convenience method to construct an instance from a string."""
        bind_addrs = set()
        for host in hosts:
            parts = host.split(':')
            name = ':'.join(parts[:-1])
            port = int(parts[-1])
            addr = (name, port)
            bind_addrs.add(addr)
        return cls(bind_addrs)

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

    def _build_control_protocol(self, host, port, family):
        logger.info('Control socket on {}:{}'.format(host, port))
        control_socket = socket.socket(family, socket.SOCK_DGRAM)
        control_socket.bind((host, port))
        return ControlProtocol(
            socket=control_socket,
            connect_cb=self._peer_connected_cb,
            disconnect_cb=self._peer_disconnected_cb)

    def _build_data_protocol(self, host, family, ctrl_protocol):
        ctrl_port = ctrl_protocol.socket.getsockname()[1]
        logger.info('Data socket on {}:{}'.format(host, ctrl_port + 1))
        data_socket = socket.socket(family, socket.SOCK_DGRAM)
        data_socket.bind((host, ctrl_port + 1))
        data_protocol = DataProtocol(data_socket, midi_command_cb=self._midi_command_cb)
        ctrl_protocol.associate_data_protocol(data_protocol)
        return data_protocol

    def _init_protocols(self):
        for host, port in self.bind_addrs:
            if utils.is_ipv4_address(host):
                family = socket.AF_INET
            elif utils.is_ipv6_address(host):
                family = socket.AF_INET6
            else:
                raise ValueError('Invalid bind host: "{}"'.format(host))

            ctrl_protocol = self._build_control_protocol(host, port, family)
            data_protocol = self._build_data_protocol(host, family, ctrl_protocol)

            self.socket_map[data_protocol.socket] = data_protocol
            self.socket_map[ctrl_protocol.socket] = ctrl_protocol

            protos = (ctrl_protocol, data_protocol)
            if family == socket.AF_INET:
                self.ipv4_protocols = protos
            elif family == socket.AF_INET6:
                self.ipv6_protocols = protos

    def _loop_once(self, timeout=None):
        sockets = self.socket_map.keys()
        rr, _, _ = select.select(sockets, [], [], timeout)
        for s in rr:
            buffer, addr = s.recvfrom(1024)
            buffer = bytes(buffer)
            proto = self.socket_map[s]
            proto.handle_message(buffer, addr)

    def serve_forever(self):
        self._init_protocols()
        while True:
            self._loop_once()


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

    bind_addrs = options.bind_addrs
    if not bind_addrs:
        bind_addrs = [DEFAULT_BIND_ADDR]

    server = Server.from_bind_addrs(bind_addrs)
    server.add_handler(ExampleHandler())

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Got CTRL-C, quitting')
        sys.exit(0)
