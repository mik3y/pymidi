from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from unittest import TestCase
from pymidi import protocol


def h2b(s):
    if hasattr(s, 'decode'):
        return s.decode('hex')
    return bytes.fromhex(s)


EXCHANGE_PACKET = h2b('ffff494e000000026633487347d810966d626f6f6b2d73657373696f6e00')
TIMESTAMP_PACKET = h2b('ffff434b47d8109602000000000000004400227e00000dfaad1e5c820000000044002288')
MIDI_PACKET = h2b('806142723be6933947d8109646803b000a39002042550011080567b52db940bb4bbc43be3109a0')


class TestPackets(TestCase):
    def test_exchange_packet(self):
        pkt = protocol.ExchangePacket.parse(EXCHANGE_PACKET)
        self.assertEqual(b'\xff\xff', pkt.preamble)
        self.assertEqual('IN', pkt.command)
        self.assertEqual(2, pkt.protocol_version)
        self.assertEqual(1714636915, pkt.initiator_token)
        self.assertEqual(1205342358, pkt.ssrc)
        self.assertEqual('mbook-session', pkt.name)

    def test_timestamp_packet(self):
        pkt = protocol.TimestampPacket.parse(TIMESTAMP_PACKET)
        self.assertEqual(b'\xff\xff', pkt.preamble)
        self.assertEqual('CK', pkt.command)
        self.assertEqual(1205342358, pkt.ssrc)
        self.assertEqual(2, pkt.count)
        self.assertEqual(1140859518, pkt.timestamp_1)
        self.assertEqual(15370297433218, pkt.timestamp_2)
        self.assertEqual(1140859528, pkt.timestamp_3)

    def test_midi_packet(self):
        pkt = protocol.MIDIPacket.parse(MIDI_PACKET)
        self.assert_(pkt.header, 'Expected a header')
        self.assertEqual(2, pkt.header.rtp_header.flags.v)
        self.assertEqual(False, pkt.header.rtp_header.flags.p)
        self.assertEqual(False, pkt.header.rtp_header.flags.x)
        self.assertEqual(0, pkt.header.rtp_header.flags.cc)
        self.assertEqual(False, pkt.header.rtp_header.flags.m)
        self.assertEqual(0x61, pkt.header.rtp_header.flags.pt)
        self.assertEqual(17010, pkt.header.rtp_header.sequence_number)

        self.assert_(pkt.command, 'Expected a command')
        self.assert_(not pkt.journal, 'Expected no journal')
