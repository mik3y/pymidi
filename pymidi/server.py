"""Midi server implementation.

References:
    * https://en.wikipedia.org/wiki/RTP-MIDI
    * http://www.raveloxprojects.com/blog/?tag=applemidi
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import select
import socket
import sys

from pymidi.protocol import DataProtocol
from pymidi.protocol import ControlProtocol

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pymidi.server')


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
                logger.info('CTRL<: {}'.format(buffer.encode('hex')))
                control_protocol.handle_message(buffer, addr)
            elif s is data_socket:
                logger.info('DATA<: {}'.format(buffer.encode('hex')))
                data_protocol.handle_message(buffer, addr)
            else:
                raise ValueError('Unknown socket.')


if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        logger.info('Got CTRL-C, quitting')
        sys.exit(0)
