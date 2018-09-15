from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import binascii
import logging
import random
import time

from construct import Struct, Const, PaddedString, CString, Padding, Int8ub, Int16ub, Int32ub
from construct import Int64ub, Bitwise, BitStruct, BitsInteger, Nibble, Flag, Optional
from construct import If, IfThenElse, GreedyBytes, GreedyRange, VarInt
from construct import this as _this

logger = logging.getLogger('pymidi.protocol')


ExchangePacket = Struct(
    'preamble' / Const(b'\xff\xff'),
    'command' / PaddedString(2, 'ascii'),
    'protocol_version' / Int32ub,
    'initiator_token' / Int32ub,
    'ssrc' / Int32ub,
    'name' / Optional(CString('ascii')),
)

TimestampPacket = Struct(
    'preamble' / Const(b'\xff\xff'),
    'command' / PaddedString(2, 'ascii'),
    'ssrc' / Int32ub,
    'count' / Int8ub,
    'padding' / Padding(3),
    'timestamp_1' / Int64ub,
    'timestamp_2' / Int64ub,
    'timestamp_3' / Int64ub,
)

MIDIPacketHeader = Struct(
    'rtp_header' / Struct(
        'flags' / Bitwise(Struct(
            'v' / BitsInteger(2),  # always 0x2
            'p' / Flag,  # always 0
            'x' / Flag,  # always 0
            'cc' / Nibble,  # always 0
            'm' / Flag,  # always 0x1
            'pt' / BitsInteger(7),  # always 0x61
        )),
        'sequence_number' / Int16ub,  # always 'K'
    ),
    'timestamp' / Int32ub,
    'ssrc' / Int32ub,
)


MIDIPacketCommand = Struct(
    'flags' / BitStruct(
        'b' / Flag,
        'j' / Flag,
        'z' / Flag,
        'p' / Flag,
        'len' / IfThenElse(_this.b == 0, BitsInteger(4), BitsInteger(12)),
    ),
    # 'midi_list' / Bytes(_this.flags.len),
    'midi_list' / GreedyRange(Struct(
        'delta_time' / If(_this._index != 0 or not _this.flags.z, VarInt),
        'command' / BitStruct(
            'command' / Nibble,
            'channel' / Nibble,
        ),
        'param1' / Int8ub,
        'param2' / Int8ub,
    )),
)

MIDIPacketJournal = Struct(
    'header' / BitStruct(
        's' / Flag,
        'y' / Flag,
        'a' / Flag,
        'h' / Flag,
        'totchan' / BitsInteger(4),
        'checkpoint_seqnum' / BitsInteger(12),
    ),
    'remain' / GreedyBytes,
)

MIDIPacket = Struct(
    'header' / MIDIPacketHeader,
    'command' / MIDIPacketCommand,
    'journal' / Optional(MIDIPacketJournal),
)


class ProtocolError(Exception):
    pass


class BaseProtocol(object):
    def __init__(self, socket, name='pymidi', ssrc=None):
        self.socket = socket
        self.name = name
        self.initialized = False
        self.ssrc = ssrc or random.randint(0, 2 ** 32 - 1)
        self.logger = logging.getLogger('midi:{}'.format(self.__class__.__name__))

    def handle_message(self, data, addr):
        if not self.initialized:
            self.state_initial(data, addr)
            self.initialized = True
            return

    def state_initial(self, data, addr):
        packet = ExchangePacket.parse(data)
        logging.debug(packet)
        if packet.command != 'IN':
            raise ProtocolError('Unrecognized command: {}'.format(packet.command))

        response = ExchangePacket.build(dict(
            command='OK',
            protocol_version=2,
            initiator_token=packet.initiator_token,
            ssrc=self.ssrc,
            name=self.name,
        ))
        logging.debug('>> {}'.format(binascii.hexlify(response)))
        self.socket.sendto(response, addr)


class ControlProtocol(BaseProtocol):
    pass


class DataProtocol(BaseProtocol):
    def __init__(self, *args, **kwargs):
        super(DataProtocol, self).__init__(*args, **kwargs)

    def handle_message(self, data, addr):
        if data[:2] == b'\xff\xff':
            command = data[2:4]
            if command == 'CK':
                self.handle_timestamp(data, addr)
            else:
                super(DataProtocol, self).handle_message(data, addr)
        else:
            self.handle_midi_packet(data, addr)

    def handle_timestamp(self, data, addr):
        packet = TimestampPacket.parse(data)
        logging.debug(packet)
        response = None

        now = int(time.time() * 10000)  # units of 100 microseconds
        if packet.count == 0:
            response = TimestampPacket.build(dict(
                command='CK',
                count=1,
                ssrc=self.ssrc,
                timestamp_1=packet.timestamp_1,
                timestamp_2=now,
                timestamp_3=0,
            ))
            logging.debug('>> {}'.format(binascii.hexlify(response)))
            self.socket.sendto(response, addr)
        elif packet.count == 2:
            offset_estimate = ((packet.timestamp_3 + packet.timestamp_1) / 2) - packet.timestamp_2
            logging.debug('offset estimate: {}'.format(offset_estimate))

    def handle_midi_packet(self, data, addr):
        packet = MIDIPacket.parse(data)
        logging.debug(packet)
