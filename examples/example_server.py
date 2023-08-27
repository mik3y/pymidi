from builtins import bytes

from optparse import OptionParser
import logging
import select
import socket
import sys

import pymidi.server
from pymidi.protocol import DataProtocol
from pymidi.protocol import ControlProtocol
from pymidi import utils

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

logger = logging.getLogger('pymidi.examples.server')

DEFAULT_BIND_ADDR = '0.0.0.0:5051'

parser = OptionParser()
parser.add_option(
    '-b',
    '--bind_addr',
    dest='bind_addrs',
    action='append',
    default=None,
    help='<ip>:<port> for listening; may give multiple times; default {}'.format(DEFAULT_BIND_ADDR),
)
parser.add_option(
    '-v', '--verbose', action='store_true', dest='verbose', default=False, help='show verbose logs'
)


def main():
    options, args = parser.parse_args()

    log_level = logging.DEBUG if options.verbose else logging.INFO
    if coloredlogs:
        coloredlogs.install(level=log_level)
    else:
        logging.basicConfig(level=log_level)

    class ExampleHandler(pymidi.server.Handler):
        """Example handler.

        This handler doesn't do all that much; we're just using one here to
        illustrate the handler interface, so you can write a much cooler one.
        """

        def __init__(self):
            self.logger = logging.getLogger('ExampleHandler')

        def on_peer_connected(self, peer):
            self.logger.info('Peer connected: {}'.format(peer))

        def on_peer_disconnected(self, peer):
            self.logger.info('Peer disconnected: {}'.format(peer))

        def on_midi_commands(self, peer, midi_packet):
            for command in midi_packet.command.midi_list:
                if command.command == 'note_on':
                    key = command.params.key
                    velocity = command.params.velocity
                    print('Someone hit the key {} with velocity {}'.format(key, velocity))

    bind_addrs = options.bind_addrs
    if not bind_addrs:
        bind_addrs = [DEFAULT_BIND_ADDR]

    server = pymidi.server.Server.from_bind_addrs(bind_addrs)
    server.add_handler(ExampleHandler())

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Got CTRL-C, quitting')
        sys.exit(0)


main()
