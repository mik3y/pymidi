from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import socket
from six import string_types
from builtins import bytes


def h2b(s):
    """Converts a hex string to bytes; Python 2/3 compatible."""
    return bytes.fromhex(s)


def b2h(b):
    """Converts a `bytes` object to a hex string."""
    if not isinstance(b, bytes):
        raise ValueError('Argument must be a `bytes`')
    result = codecs.getencoder('hex_codec')(b)[0]
    if isinstance(result, bytes):
        result = result.decode('ascii')
    return result


def is_ipv4_address(ipstr):
    try:
        socket.inet_aton(ipstr)
        return True
    except (socket.error, TypeError):
        return False


def is_ipv6_address(ipstr):
    try:
        socket.inet_pton(socket.AF_INET6, ipstr)
        return True
    except (socket.error, TypeError):
        return False


def is_ipv4_or_ipv6_address(ipstr):
    return is_ipv4_address(ipstr) or is_ipv6_address(ipstr)


def validate_addr(addr):
    """Raises `ValueError` if `addr` is not a well-formed (ip, port) pair."""
    if not isinstance(addr, tuple):
        raise ValueError('Address {} is not a tuple'.format(repr(addr)))
    if len(addr) != 2:
        raise ValueError('Address {} is not a 2-tuple'.format(repr(addr)))
    if not isinstance(addr[0], string_types):
        raise ValueError('First param of address {} is not a string'.format(repr(addr)))
    if not is_ipv4_or_ipv6_address(addr[0]):
        raise ValueError('First param of address {} is not a valid ip'.format(repr(addr)))
    if not isinstance(addr[1], int):
        raise ValueError('Second param of address {} is not an int'.format(repr(addr)))
