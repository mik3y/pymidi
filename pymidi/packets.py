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
    name = pkt._name
    detail = ''

    if name == 'AppleMIDIExchangePacket':
        detail = '[command={} ssrc={} name={}]'.format(pkt.command, pkt.ssrc, pkt.name)
    elif name == 'MIDIPacket':
        items = []
        for entry in pkt.command.midi_list:
            command = entry.command
            if command in ('note_on', 'note_off'):
                items.append('{} {} {}'.format(command, entry.params.key, entry.params.velocity))
            elif command == 'control_mode_change':
                items.append('{} {} {}'.format(
                    command, entry.params.controller, entry.params.value))
            else:
                items.append(command)
        detail = ' '.join(('[{}]'.format(i) for i in items))

    return '{} {}'.format(name, detail)


def remember_last(obj, ctx):
    """Stores the last-seen command byte in the parsing context.

    Bit of a hack to make running status support work.
    """
    setattr(ctx._root, '_last_command_byte', obj)


AppleMIDIExchangePacket = Struct(
    '_name' / Computed('AppleMIDIExchangePacket'),
    'preamble' / Const(b'\xff\xff'),
    'command' / PaddedString(2, 'ascii'),
    'protocol_version' / Int32ub,
    'initiator_token' / Int32ub,
    'ssrc' / Int32ub,
    'name' / Optional(CString('ascii')),
)

AppleMIDITimestampPacket = Struct(
    '_name' / Computed('AppleMIDITimestampPacket'),
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
    '_name' / Computed('MIDIPacketHeader'),
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

MIDINote = Enum(Byte,
    Cn1=0,
    Csn1=1,
    Dn1=2,
    Dsn1=3,
    En1=4,
    Fn1=5,
    Fsn1=6,
    Gn1=7,
    Gsn1=8,
    An1=9,
    Asn1=10,
    Bn1=11,
    C0=12,
    Cs0=13,
    D0=14,
    Ds0=15,
    E0=16,
    F0=17,
    Fs0=18,
    G0=19,
    Gs0=20,
    A0=21,
    As0=22,
    B0=23,
    C1=24,
    Cs1=25,
    D1=26,
    Ds1=27,
    E1=28,
    F1=29,
    Fs1=30,
    G1=31,
    Gs1=32,
    A1=33,
    As1=34,
    B1=35,
    C2=36,
    Cs2=37,
    D2=38,
    Ds2=39,
    E2=40,
    F2=41,
    Fs2=42,
    G2=43,
    Gs2=44,
    A2=45,
    As2=46,
    B2=47,
    C3=48,
    Cs3=49,
    D3=50,
    Ds3=51,
    E3=52,
    F3=53,
    Fs3=54,
    G3=55,
    Gs3=56,
    A3=57,
    As3=58,
    B3=59,
    C4=60,
    Cs4=61,
    D4=62,
    Ds4=63,
    E4=64,
    F4=65,
    Fs4=66,
    G4=67,
    Gs4=68,
    A4=69,
    As4=70,
    B4=71,
    C5=72,
    Cs5=73,
    D5=74,
    Ds5=75,
    E5=76,
    F5=77,
    Fs5=78,
    G5=79,
    Gs5=80,
    A5=81,
    As5=82,
    B5=83,
    C6=84,
    Cs6=85,
    D6=86,
    Ds6=87,
    E6=88,
    F6=89,
    Fs6=90,
    G6=91,
    Gs6=92,
    A6=93,
    As6=94,
    B6=95,
    C7=96,
    Cs7=97,
    D7=98,
    Ds7=99,
    E7=100,
    F7=101,
    Fs7=102,
    G7=103,
    Gs7=104,
    A7=105,
    As7=106,
    B7=107,
    C8=108,
    Cs8=109,
    D8=110,
    Ds8=111,
    E8=112,
    F8=113,
    Fs8=114,
    G8=115,
    Gs8=116,
    A8=117,
    As8=118,
    B8=119,
    C9=120,
    Cs9=121,
    D9=122,
    Ds9=123,
    E9=124,
    F9=125,
    Fs9=126,
    G9=127)

MIDIPacketCommand = Struct(
    '_name' / Computed('MIDIPacketCommand'),
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
                'key' / MIDINote,
                'velocity' / Int8ub,
            ),
            'note_off': Struct(
                'key' / MIDINote,
                'velocity' / Int8ub,
            ),
            'aftertouch': Struct(
                'key' / MIDINote,
                'touch' / Int8ub,
            ),
            'control_mode_change': Struct(
                'controller' / Int8ub,
                'value' / Int8ub,
            ),
        }, default=Struct(
            'unknown' / GreedyBytes,
        ))),
    )),
)

MIDISystemJournal = Struct(
    '_name' / Computed('MIDISystemJournal'),
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
    '_name' / Computed('MIDIChapterJournal'),
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
    '_name' / Computed('MIDIPacketJournal'),
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
    '_name' / Computed('MIDIPacket'),
    'header' / MIDIPacketHeader,
    'command' / MIDIPacketCommand,
    'journal' / If(_this.command.flags.j, MIDIPacketJournal),
)
