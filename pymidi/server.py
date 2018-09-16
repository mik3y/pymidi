from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from optparse import OptionParser
import logging
import select
import socket
import sys

from pymidi.protocol import DataProtocol
from pymidi.protocol import ControlProtocol

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

logger = logging.getLogger('pymidi.server')

parser = OptionParser()
parser.add_option('-p', '--port',
    type='int',
    dest='port',
    default=5051,
    help='server command port; port + 1 will also be used')
parser.add_option('-b', '--bind_host',
    dest='host',
    default='0.0.0.0',
    help='bind to this address')
parser.add_option('-v', '--verbose',
    action='store_true',
    dest='verbose',
    default=False,
    help='show verbose logs')


def run_server(port=5051, host='0.0.0.0'):
    logger.info('Control socket on {}:{}'.format(host, port))
    control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_socket.bind((host, port))
    control_protocol = ControlProtocol(control_socket)

    port = port + 1

    logger.info('Data socket on {}:{}'.format(host, port))
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data_socket.bind((host, port))
    data_protocol = DataProtocol(data_socket)

    while True:
        rr, _, _ = select.select([control_socket, data_socket], [], [])
        for s in rr:
            buffer, addr = s.recvfrom(1024)
            if s is control_socket:
                control_protocol.handle_message(buffer, addr)
            elif s is data_socket:
                data_protocol.handle_message(buffer, addr)
            else:
                raise ValueError('Unknown socket.')


if __name__ == '__main__':
    options, args = parser.parse_args()

    log_level = logging.DEBUG if options.verbose else logging.INFO
    if coloredlogs:
        coloredlogs.install(level=log_level)
    else:
        logging.basicConfig(level=log_level)

    try:
        run_server(port=options.port, host=options.host)
    except KeyboardInterrupt:
        logger.info('Got CTRL-C, quitting')
        sys.exit(0)
