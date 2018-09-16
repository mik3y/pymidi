from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import binascii
import logging
import random
import time

from pymidi import packets

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
    def __init__(self, addr, ssrc, initialized=False):
        self.addr = addr
        self.ssrc = ssrc
        self.initialized = initialized


class ProtocolError(Exception):
    pass


class BaseProtocol(object):
    def __init__(self, socket, name='pymidi', ssrc=None):
        self.socket = socket
        self.name = name
        self.initialized = False
        self.ssrc = ssrc or random.randint(0, 2 ** 32 - 1)
        self.logger = logging.getLogger('pymidi.{}'.format(self.__class__.__name__))

    def sendto(self, message, addr):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('tx: {}'.format(binascii.hexlify(message)))
        self.socket.sendto(message, addr)

    def handle_message(self, data, addr):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('rx: {}'.format(data.encode('hex')))

        if data[0:2] == APPLEMIDI_PREAMBLE:
            command = data[2:4]
            self.logger.info('Command: {}'.format(command))
            self.handle_command_message(command, data, addr)
        else:
            self.handle_data_message(data, addr)

    def handle_data_message(self, data, addr):
        self.logger.warn('Unrecognized datagram, ignoring packet')

    def handle_command_message(self, command, data, addr):
        if not self.initialized:
            self.state_initial(data, addr)
            self.initialized = True

    def state_initial(self, data, addr):
        packet = packets.AppleMIDIExchangePacket.parse(data)
        if self.logger.isEnabledFor(logging.DEBUG):
            logging.debug(packet)
        if packet.command != APPLEMIDI_COMMAND_INVITATION:
            self.logger.warning('Unrecognized command: {}'.format(packet.command))
            return

        response = packets.AppleMIDIExchangePacket.build(dict(
            command=APPLEMIDI_COMMAND_INVITATION_ACCEPTED,
            protocol_version=2,
            initiator_token=packet.initiator_token,
            ssrc=self.ssrc,
            name=self.name,
        ))
        self.sendto(response, addr)


class ControlProtocol(BaseProtocol):
    pass


class DataProtocol(BaseProtocol):
    def __init__(self, *args, **kwargs):
        super(DataProtocol, self).__init__(*args, **kwargs)

    def handle_command_message(self, command, data, addr):
        if command == APPLEMIDI_COMMAND_TIMESTAMP_SYNC:
            self.handle_timestamp(data, addr)
        else:
            super(DataProtocol, self).handle_command_message(command, data, addr)

    def handle_data_message(self, data, addr):
        packet = packets.MIDIPacket.parse(data)
        self.logger.info(packets.to_string(packet))
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(packet)

    def handle_timestamp(self, data, addr):
        packet = packets.AppleMIDITimestampPacket.parse(data)
        logging.debug(packet)
        response = None

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