from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import binascii
import logging
import random
import time

from construct import Struct, Const, PaddedString, CString, Padding, Int8ub, Int16ub, Int32ub
from construct import Int64ub, Bitwise, BitStruct, BitsInteger, Nibble, Flag, Optional, Bytes
from construct import If, IfThenElse, GreedyBytes, GreedyRange, VarInt, FixedSized, Byte, Computed
from construct import Switch, Enum, Peek
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

COMMAND_NOTE_OFF = 0x80
COMMAND_NOTE_ON = 0x90
COMMAND_AFTERTOUCH = 0xA0
COMMAND_CONTROL_MODE_CHANGE = 0xB0


# Global that stores the last-seen status, for running status support.
# TODO(mikey): This *should* be possible without any state, by peeking
# at the struct under construction; haven't figured it out.
last_command = None


def remember_last(obj, ctx):
    global last_command
    last_command = obj


MIDIPacketCommand = Struct(
    'flags' / BitStruct(
        'b' / Flag,
        'j' / Flag,
        'z' / Flag,
        'p' / Flag,
        'len' / IfThenElse(_this.b == 0, BitsInteger(4), BitsInteger(12)),
    ),
    # 'midi_list' / Bytes(_this.flags.len),
    'midi_list' / FixedSized(_this.flags.len, GreedyRange(Struct(
        'delta_time' / If(_this._index > 0, VarInt),

        # The "running status" technique means multiple commands may be sent under
        # the same status. This condition occurs when, after parsing the current
        # commands, we see the next byte is NOT a status byte (MSB is low).
        '__next' / Peek(Int8ub),
        'command_byte' / IfThenElse(_this.__next & 0x80,
            Byte * remember_last,
            Computed(lambda ctx: last_command)
        ),
        'command' / If(_this.command_byte, Enum(Computed(_this.command_byte & 0xf0),
            note_on=COMMAND_NOTE_ON,
            note_off=COMMAND_NOTE_OFF,
            aftertouch=COMMAND_AFTERTOUCH,
            control_mode_change=COMMAND_CONTROL_MODE_CHANGE)),
        'channel' / If(_this.command_byte, Computed(_this.command_byte & 0x0f)),

        'params' / Switch(_this.command, {
            'note_on': Struct(
                'key' / Byte,
                'velocity' / Byte,
            ),
            'note_off': Struct(
                'key' / Byte,
                'velocity' / Byte,
            ),
            'aftertouch': Struct(
                'key' / Byte,
                'touch' / Byte,
            ),
            'control_mode_change': Struct(
                'controller' / Byte,
                'value' / Byte,
            ),
        }, default=Struct(
            'unknown' / GreedyBytes,
        ))),
    )),
)

MIDISystemJournal = Struct(
    'header' / BitStruct(
        's' / Flag,
        'd' / Flag,
        'v' / Flag,
        'q' / Flag,
        'f' / Flag,
        'x' / Flag,
        'length' / BitsInteger(10),
    ),

    # Note from RFC 6295 appendix A1: The "length" field includes
    # the header bytes.
    'journal' / Bytes(_this.header.length - 2),
)

MIDIChapterJournal = Struct(
    'header' / BitStruct(
        's' / Flag,
        'chan' / BitsInteger(4),
        'h' / Flag,
        'length' / BitsInteger(10),
        'p' / Flag,
        'c' / Flag,
        'm' / Flag,
        'w' / Flag,
        'n' / Flag,
        'e' / Flag,
        't' / Flag,
        'a' / Flag,
    ),

    # Note from RFC 6295 appendix A1: The "length" field includes
    # the header bytes.
    'journal' / Bytes(_this.header.length - 3),
)

MIDIPacketJournal = Struct(
    'header' / BitStruct(
        's' / Flag,
        'y' / Flag,
        'a' / Flag,
        'h' / Flag,
        'totchan' / BitsInteger(4),
    ),
    'checkpoint_seqnum' / Int16ub,
    'system_journal' / If(_this.header.s, MIDISystemJournal),
    'channel_journal' / If(_this.header.a, MIDIChapterJournal),
)

MIDIPacket = Struct(
    'header' / MIDIPacketHeader,
    'command' / MIDIPacketCommand,
    'journal' / If(_this.command.flags.j, MIDIPacketJournal),
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
