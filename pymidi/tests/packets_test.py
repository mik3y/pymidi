from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from unittest import TestCase
from pymidi import packets
from pymidi.utils import h2b

EXCHANGE_PACKET = h2b('ffff494e000000026633487347d810966d626f6f6b2d73657373696f6e00')
TIMESTAMP_PACKET = h2b('ffff434b47d8109602000000000000004400227e00000dfaad1e5c820000000044002288')

# A midi packet with a Note On command
SINGLE_MIDI_PACKET = h2b('8061427a4b9f303647d8109643903026204276000608006685')

# A midi packet with two commands, utilixing running status.
#
# Commands
#   0x90 0x3e 0x41  - NOTE_ON D3 velocity 49
#   0x40 0x3b       - NOTE_ON E3 velocity 59
#
# Journal
#   NOTE_ON C3 velocity 37
MULTI_MIDI_PACKET = h2b(
    '8061429a51d2dc8747d8109646903e310a403b21427c00090881673c250d50c8060880440e'
)

# A controller/mode change packet
CONTROL_MODE_CHANGE_PACKET = h2b('80614ba55944067e47d8109643b06c00204ba0000948006c7f807708')

# An ApplieMIDI invitation packet
APPLEMIDI_INVITATION_PACKET = h2b('ffff494e000000020507236747d810966d626f6f6b2d73657373696f6e00')

# An AppleMIDI exit packet
APPLEMIDI_EXIT_PACKET = h2b('ffff4259000000020000000047d81096')


class TestPackets(TestCase):
    def test_exchange_packet(self):
        pkt = packets.AppleMIDIExchangePacket.parse(EXCHANGE_PACKET)
        self.assertEqual(b'\xff\xff', pkt.preamble)
        self.assertEqual('IN', pkt.command)
        self.assertEqual(2, pkt.protocol_version)
        self.assertEqual(1714636915, pkt.initiator_token)
        self.assertEqual(1205342358, pkt.ssrc)
        self.assertEqual('mbook-session', pkt.name)

    def test_timestamp_packet(self):
        pkt = packets.AppleMIDITimestampPacket.parse(TIMESTAMP_PACKET)
        self.assertEqual(b'\xff\xff', pkt.preamble)
        self.assertEqual('CK', pkt.command)
        self.assertEqual(1205342358, pkt.ssrc)
        self.assertEqual(2, pkt.count)
        self.assertEqual(1140859518, pkt.timestamp_1)
        self.assertEqual(15370297433218, pkt.timestamp_2)
        self.assertEqual(1140859528, pkt.timestamp_3)

    def test_single_midi_packet(self):
        pkt = packets.MIDIPacket.parse(SINGLE_MIDI_PACKET)
        print(pkt)
        self.assert_(pkt.header, 'Expected a header')
        self.assertEqual(2, pkt.header.rtp_header.flags.v)
        self.assertEqual(False, pkt.header.rtp_header.flags.p)
        self.assertEqual(False, pkt.header.rtp_header.flags.x)
        self.assertEqual(0, pkt.header.rtp_header.flags.cc)
        self.assertEqual(False, pkt.header.rtp_header.flags.m)
        self.assertEqual(0x61, pkt.header.rtp_header.flags.pt)
        self.assertEqual(17018, pkt.header.rtp_header.sequence_number)

        self.assert_(pkt.command, 'Expected a command')
        self.assertEqual(False, pkt.command.flags.b)
        self.assertEqual(True, pkt.command.flags.j)
        self.assertEqual(False, pkt.command.flags.z)
        self.assertEqual(False, pkt.command.flags.p)
        self.assertEqual(3, pkt.command.flags.len)
        print(pkt.command)
        self.assertEqual(1, len(pkt.command.midi_list))

        command = pkt.command.midi_list[0]
        self.assertEqual(0x90, command.command_byte)
        self.assertEqual('note_on', command.command)
        self.assertEqual('C3', command.params.key)
        self.assert_(38, command.params.velocity)

        self.assert_(pkt.journal, 'Expected journal')

    def test_multi_midi_packet(self):
        pkt = packets.MIDIPacket.parse(MULTI_MIDI_PACKET)
        self.assert_(pkt.header, 'Expected a header')
        self.assertEqual(2, pkt.header.rtp_header.flags.v)
        self.assertEqual(False, pkt.header.rtp_header.flags.p)
        self.assertEqual(False, pkt.header.rtp_header.flags.x)
        self.assertEqual(0, pkt.header.rtp_header.flags.cc)
        self.assertEqual(False, pkt.header.rtp_header.flags.m)
        self.assertEqual(0x61, pkt.header.rtp_header.flags.pt)
        self.assertEqual(17050, pkt.header.rtp_header.sequence_number)

        self.assert_(pkt.command, 'Expected a command')
        self.assertEqual(False, pkt.command.flags.b)
        self.assertEqual(True, pkt.command.flags.j)
        self.assertEqual(False, pkt.command.flags.z)
        self.assertEqual(False, pkt.command.flags.p)
        self.assertEqual(6, pkt.command.flags.len)
        self.assertEqual(2, len(pkt.command.midi_list))

        command = pkt.command.midi_list[0]
        self.assertEqual(0x90, command.command_byte)
        self.assertEqual('note_on', command.command)
        self.assertEqual('D4', command.params.key)
        self.assert_(38, command.params.velocity)

        command = pkt.command.midi_list[1]
        self.assertEqual(0x90, command.command_byte)
        self.assertEqual('note_on', command.command)
        self.assertEqual('E4', command.params.key)
        self.assert_(38, command.params.velocity)

        self.assert_(pkt.journal, 'Expected journal')

    def test_packet_with_no_journal(self):
        pkt = packets.MIDIPacket.parse(h2b('806142a0550d8a5a47d8109603903446'))
        self.assertEqual(False, pkt.command.flags.j, 'Expected J bit to be clear')
        self.assert_(not pkt.journal, 'Expected no journal')

    def test_to_string(self):
        pkt = packets.MIDIPacket.parse(SINGLE_MIDI_PACKET)
        strval = packets.to_string(pkt)
        self.assertEqual('MIDIPacket [note_on C3 38]', strval)

        pkt = packets.MIDIPacket.parse(MULTI_MIDI_PACKET)
        strval = packets.to_string(pkt)
        self.assertEqual('MIDIPacket [note_on D4 49] [note_on E4 59]', strval)

        pkt = packets.MIDIPacket.parse(CONTROL_MODE_CHANGE_PACKET)
        strval = packets.to_string(pkt)
        self.assertEqual('MIDIPacket [control_mode_change 108 0]', strval)

        pkt = packets.AppleMIDIExchangePacket.parse(APPLEMIDI_INVITATION_PACKET)
        strval = packets.to_string(pkt)
        self.assertEqual('AppleMIDIExchangePacket [command=IN ssrc=1205342358 name=mbook-session]',
            strval)

        pkt = packets.AppleMIDIExchangePacket.parse(APPLEMIDI_EXIT_PACKET)
        strval = packets.to_string(pkt)
        self.assertEqual('AppleMIDIExchangePacket [command=BY ssrc=1205342358 name=None]', strval)
