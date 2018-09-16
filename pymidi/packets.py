from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from construct import Struct, Const, PaddedString, CString, Padding, Int8ub, Int16ub, Int32ub
from construct import Int64ub, Bitwise, BitStruct, BitsInteger, Nibble, Flag, Optional, Bytes
from construct import If, IfThenElse, GreedyBytes, GreedyRange, VarInt, FixedSized, Byte, Computed
from construct import Switch, Enum, Peek
from construct import this as _this


COMMAND_NOTE_OFF = 0x80
COMMAND_NOTE_ON = 0x90
COMMAND_AFTERTOUCH = 0xA0
COMMAND_CONTROL_MODE_CHANGE = 0xB0


def to_string(pkt):
    """Pretty-prints a packet."""
    if not pkt.command.midi_list:
        return 'EMPTY'
    command = pkt.command.midi_list[0].command
    detail = ''
    if command in ('note_on', 'note_off'):
        notes = pkt.command.midi_list
        detail = ', '.join(('{} {}'.format(e.params.key, e.params.velocity) for e in notes))
    return '{} {}'.format(command, detail)


def remember_last(obj, ctx):
    """Stores the last-seen command byte in the parsing context.

    Bit of a hack to make running status support work.
    """
    setattr(ctx._root, '_last_command_byte', obj)


AppleMIDIExchangePacket = Struct(
    'preamble' / Const(b'\xff\xff'),
    'command' / PaddedString(2, 'ascii'),
    'protocol_version' / Int32ub,
    'initiator_token' / Int32ub,
    'ssrc' / Int32ub,
    'name' / Optional(CString('ascii')),
)

AppleMIDITimestampPacket = Struct(
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
    'midi_list' / FixedSized(_this.flags.len, GreedyRange(Struct(
        'delta_time' / If(_this._index > 0, VarInt),

        # The "running status" technique means multiple commands may be sent under
        # the same status. This condition occurs when, after parsing the current
        # commands, we see the next byte is NOT a status byte (MSB is low).
        #
        # Below, this is accomplished by storing the most recent status byte
        # on the global context with the `* remember_last` macro; then using it
        # on the `else` branch of the `command_byte` selection.
        '__next' / Peek(Int8ub),
        'command_byte' / IfThenElse(_this.__next & 0x80,
            Byte * remember_last,
            Computed(lambda ctx: ctx._root._last_command_byte)
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
