from builtins import bytes

from optparse import OptionParser
import logging
import select
import socket
import sys
import random
import time

from pymidi import packets
from pymidi import protocol
from pymidi import utils
from pymidi.utils import b2h
from construct import ConstructError

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

logger = logging.getLogger('pymidi.client')


class ClientError(Exception):
    """General client error."""


class AlreadyConnected(ClientError):
    """Client is already connected."""


class Client(object):
    def __init__(self, name='PyMidi', ssrc=None):
        """Creates a new Client instance."""
        self.ssrc = ssrc or random.randint(0, 2 ** 32 - 1)
        self.socket = None
        self.host = None
        self.port = None

    def connect(self, host, port):
        if self.host and self.port:
            raise ClientError(f'Already connected to {self.host}:{self.port}')

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pkt = packets.AppleMIDIExchangePacket.create(
            protocol_version=2,
            command=protocol.APPLEMIDI_COMMAND_INVITATION,
            initiator_token=random.randint(0, 2 ** 32 - 1),
            ssrc=self.ssrc,
        )
        for target_port in (port, port + 1):
            logger.info(f'Sending exchange packet to port {target_port}...')
            self.socket.sendto(pkt, (host, target_port))
            packet = self.get_next_packet()
            if not packet:
                raise Exception('No packet received')
            if packet._name != 'AppleMIDIExchangePacket':
                raise Exception('Expected exchange packet')
            logger.info(f'Exchange successful.')

        self.host = host
        self.port = port

    def sync_timestamps(self, port):
        ts1 = int(time.time() * 1000)
        packet = packets.AppleMIDITimestampPacket.create(
            command=protocol.APPLEMIDI_COMMAND_TIMESTAMP_SYNC,
            ssrc=self.ssrc,
            count=count,
            padding=0,
            timestamp_1=ts1,
            timestamp_2=0,
            timestamp_3=0,
        )

    def send_note_on(self, notestr, velocity=80, channel=1):
        self._send_note(notestr, packets.COMMAND_NOTE_ON, velocity, channel)

    def send_note_off(self, notestr, velocity=80, channel=1):
        self._send_note(notestr, packets.COMMAND_NOTE_OFF, velocity, channel)

    def _send_note(self, notestr, command, velocity=80, channel=1):
        # key = packets.MIDINote.build(notestr)
        command = {
            'flags': {
                'b': 0,
                'j': 0,
                'z': 0,
                'p': 0,
                'len': 3,
            },
            'midi_list': [
                {
                    'delta_time': 0,
                    '__next': 0x80,  # TODO(mikey): This shouldn't be needed.
                    'command': 'note_on' if command == packets.COMMAND_NOTE_ON else 'note_off',
                    'command_byte': command | (channel & 0xF),
                    'channel': channel,
                    'params': {
                        'key': notestr,
                        'velocity': velocity,
                    },
                }
            ],
        }
        self._send_rtp_command(command)

    def _send_rtp_command(self, command):
        header = packets.MIDIPacketHeader.create(
            rtp_header={
                'flags': {
                    'v': 0x2,
                    'p': 0,
                    'x': 0,
                    'cc': 0,
                    'm': 0x1,
                    'pt': 0x61,
                },
                'sequence_number': ord('K'),
            },
            timestamp=int(time.time()),
            ssrc=self.ssrc,
        )

        packet = packets.MIDIPacket.create(
            header={
                'rtp_header': {
                    'flags': {
                        'v': 0x2,
                        'p': 0,
                        'x': 0,
                        'cc': 0,
                        'm': 0x1,
                        'pt': 0x61,
                    },
                    'sequence_number': ord('K'),
                },
                'timestamp': int(time.time()),
                'ssrc': self.ssrc,
            },
            command=command,
            journal='',
        )

        self.socket.sendto(packet, (self.host, self.port + 1))

    def get_next_packet(self):
        data, addr = self.socket.recvfrom(1024)
        command = data[2:4]
        try:
            if data[0:2] == protocol.APPLEMIDI_PREAMBLE:
                command = data[2:4]
                logger.debug('Command: {}'.format(b2h(command)))
                return self.handle_command_message(command, data, addr)
        except ConstructError:
            logger.exception('Bug or malformed packet, ignoring')
        return None

    def handle_command_message(self, command, data, addr):
        if command == protocol.APPLEMIDI_COMMAND_INVITATION_ACCEPTED:
            return packets.AppleMIDIExchangePacket.parse(data)
        else:
            logger.warning('Ignoring unrecognized command: {}'.format(command))
        return None
