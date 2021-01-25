from builtins import bytes

from optparse import OptionParser
import logging
import select
import socket
import sys
import time

import pymidi.client
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

    client = pymidi.client.Client()
    host = '0.0.0.0'
    port = 5004
    logger.info(f'Connecting to RTP-MIDI server @ {host}:{port} ...')
    client.connect('0.0.0.0', port)
    logger.info('Connecting!')
    while True:
        logger.info('Striking key...')
        client.send_note_on('B6')
        time.sleep(0.5)
        client.send_note_off('B6')
        time.sleep(0.5)


main()
