from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import binascii
import logging
import random
import time

from pymidi import packets
from construct import ConstructError

# Command messages are preceded with this sequence.
APPLEMIDI_PREAMBLE = b'\xff\xff'

# Two-byte RTP-MIDI control commands
APPLEMIDI_COMMAND_INVITATION = 'IN'
APPLEMIDI_COMMAND_INVITATION_ACCEPTED = 'OK'
APPLEMIDI_COMMAND_INVITATION_REJECTED = 'NO'
APPLEMIDI_COMMAND_TIMESTAMP_SYNC = 'CK'
APPLEMIDI_COMMAND_EXIT = 'BY'


class Peer(object):
    """Holds state about a midi peer."""
    def __init__(self, name, addr, ssrc):
        self.name = name
        self.addr = addr
        self.ssrc = ssrc

    def __str__(self):
        return '{} (ssrc={}, addr={})'.format(self.name, self.ssrc, self.addr)


class ProtocolError(Exception):
    pass


class BaseProtocol(object):
    def __init__(self, socket, name='pymidi', ssrc=None, connect_cb=None, disconnect_cb=None):
        self.socket = socket
        self.name = name
        self.peers_by_ssrc = {}
        self.ssrc = ssrc or random.randint(0, 2 ** 32 - 1)
        self.connect_cb = connect_cb
        self.disconnect_cb = disconnect_cb
        self.logger = logging.getLogger('pymidi.{}'.format(self.__class__.__name__))

    def _connect_peer(self, name, addr, ssrc):
        peer = Peer(name=name, addr=addr, ssrc=ssrc)
        self.peers_by_ssrc[ssrc] = peer
        if self.connect_cb:
            self.connect_cb(peer)
        return peer

    def _disconnect_peer(self, ssrc):
        peer = self.peers_by_ssrc.pop(ssrc)
        if peer and self.disconnect_cb:
            self.disconnect_cb(peer)
        return peer

    def sendto(self, message, addr):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('tx: {}'.format(binascii.hexlify(message)))
        self.socket.sendto(message, addr)

    def handle_message(self, data, addr):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('rx: {}'.format(data.encode('hex')))

        try:
            if data[0:2] == APPLEMIDI_PREAMBLE:
                command = data[2:4]
                self.logger.debug('Command: {}'.format(command))
                self.handle_command_message(command, data, addr)
            else:
                self.handle_data_message(data, addr)
        except ConstructError as e:
            self.logger.warning('Bug or malformed packet, ignoring: {}'.format(e))

    def handle_data_message(self, data, addr):
        pass

    def handle_command_message(self, command, data, addr):
        if command == APPLEMIDI_COMMAND_INVITATION:
            packet = packets.AppleMIDIExchangePacket.parse(data)
            ssrc = packet.ssrc
            if ssrc in self.peers_by_ssrc:
                self.logger.warning('Ignoring duplicate connection from ssrc {}'.format(ssrc))
                return
            peer = self._connect_peer(name=packet.name, addr=addr, ssrc=ssrc)
            response = packets.AppleMIDIExchangePacket.build(dict(
                command=APPLEMIDI_COMMAND_INVITATION_ACCEPTED,
                protocol_version=2,
                initiator_token=packet.initiator_token,
                ssrc=self.ssrc,
                name=self.name,
            ))
            self.sendto(response, addr)
            self.logger.info('Accepted connection from {}'.format(peer))
        elif command == APPLEMIDI_COMMAND_EXIT:
            packet = packets.AppleMIDIExchangePacket.parse(data)
            ssrc = packet.ssrc
            if ssrc not in self.peers_by_ssrc:
                self.logger.warning('Ignoring exit from unknown ssrc {}'.format(ssrc))
                return
            peer = self._disconnect_peer(ssrc)
            self.logger.info('Peer {} exited'.format(peer))
        else:
            self.logger.warning('Ignoring unrecognized command: {}'.format(command))


class ControlProtocol(BaseProtocol):
    def __init__(self, data_protocol=None, *args, **kwargs):
        super(ControlProtocol, self).__init__(*args, **kwargs)
        self.data_protocol = data_protocol

    def associate_data_protocol(self, data_protocol):
        self.data_protocol = data_protocol

    def _disconnect_peer(self, ssrc):
        """Disconnect from data protocol when disconnecting locally."""
        peer = super(ControlProtocol, self)._disconnect_peer(ssrc)
        if peer:
            self.data_protocol._disconnect_peer(ssrc)
        return peer


class DataProtocol(BaseProtocol):
    def __init__(self, *args, **kwargs):
        self.midi_command_cb = kwargs.pop('midi_command_cb', None)
        super(DataProtocol, self).__init__(*args, **kwargs)

    def handle_command_message(self, command, data, addr):
        if command == APPLEMIDI_COMMAND_TIMESTAMP_SYNC:
            self.handle_timestamp(data, addr)
        else:
            super(DataProtocol, self).handle_command_message(command, data, addr)

    def handle_data_message(self, data, addr):
        packet = packets.MIDIPacket.parse(data)
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(packet)
        peer = self.peers_by_ssrc.get(packet.header.ssrc)
        if not peer:
            self.logger.debug('Ignoring message from unknown ssrc={}'.format(packet.header.ssrc))
            return
        if self.midi_command_cb:
            self.midi_command_cb(peer, packet)

    def handle_timestamp(self, data, addr):
        packet = packets.AppleMIDITimestampPacket.parse(data)
        response = None
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(packet)

        now = int(time.time() * 10000)  # units of 100 microseconds
        if packet.count == 0:
            response = packets.AppleMIDITimestampPacket.build(dict(
                command=APPLEMIDI_COMMAND_TIMESTAMP_SYNC,
                count=1,
                ssrc=self.ssrc,
                timestamp_1=packet.timestamp_1,
                timestamp_2=now,
                timestamp_3=0,
            ))
            self.sendto(response, addr)
        elif packet.count == 2:
            offset_estimate = ((packet.timestamp_3 + packet.timestamp_1) / 2) - packet.timestamp_2
            self.logger.debug('offset estimate: {}'.format(offset_estimate))
