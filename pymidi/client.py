from builtins import bytes

from optparse import OptionParser
import logging
import select
import socket
import sys
import random

from pymidi import packets
from pymidi import protocol
from pymidi import utils
from pymidi.utils import b2h
from pymidi.utils import get_timestamp
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
    def __init__(self, name='PyMidi', ssrc=None, sourcePort=None):
        """Creates a new Client instance."""
        self.ssrc = ssrc or random.randint(0, 2 ** 32 - 1)
        self.socket = [None,None] # Need to have a command and data socket on the client side
        self.host = None
        self.port = None
        self.sourcePort = sourcePort or 5004
        self.name = name or 'PyMidi'
        self.sequenceNumber = 1

    def connect(self, host, port):
        if self.host and self.port:
            raise ClientError(f'Already connected to {self.host}:{self.port}')

        pkt = packets.AppleMIDIExchangePacket.create(
            protocol_version=2,
            command=protocol.APPLEMIDI_COMMAND_INVITATION,
            initiator_token=random.randint(0, 2 ** 32 - 1),
            ssrc=self.ssrc,
            name=self.name
        )

        for index in (0, 1):
            self.socket[index] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket[index].bind(('0.0.0.0', self.sourcePort+index))

            logger.info(f'Sending exchange packet to port {port+index} from port {self.sourcePort+index}...')
            self.socket[index].sendto(pkt, (host, port+index))
            packet = self.get_next_packet(self.socket[index])
            if not packet:
                raise Exception('No packet received')
            if packet._name != 'AppleMIDIExchangePacket':
                raise Exception('Expected exchange packet')
            logger.info(f'Exchange successful.')

        self.host = host
        self.port = port

    def disconnect(self):
        if not self.socket[0]:
            raise ClientError(f'Not connected to anywhere')

        pkt = packets.AppleMIDIExchangePacket.create(
            protocol_version=2,
            command=protocol.APPLEMIDI_COMMAND_EXIT,
            initiator_token=0,
            ssrc=self.ssrc,
            name=None
        )
        self.socket[0].sendto(pkt, (self.host, self.port))

        for index in (0, 1): self.socket[index].close()

        self.socket = [None,None]
        self.host = None
        self.port = None

    def sync_timestamps(self, port):
        packet = packets.AppleMIDITimestampPacket.create(
            command=protocol.APPLEMIDI_COMMAND_TIMESTAMP_SYNC,
            ssrc=self.ssrc,
            count=count,
            padding=0,
            timestamp_1=get_timestamp(),
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
        self._send_rtp_command(self.socket[1], command)

    def _send_rtp_command(self, socket, command):
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
                    'sequence_number': self.sequenceNumber,
                },
                'timestamp': get_timestamp(),
                'ssrc': self.ssrc,
            },
            command=command,
            journal='',
        )

        socket.sendto(packet, (self.host, self.port + 1))
        self.sequenceNumber += 1

    def get_next_packet(self, socket):
        data, addr = socket.recvfrom(1024)
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
