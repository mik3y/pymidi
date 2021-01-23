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
            disconnect_cb=self._peer_disconnected_cb,
        )

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
