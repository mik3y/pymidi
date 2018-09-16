from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


def h2b(s):
    """Converts a hex string to bytes; Python 2/3 compatible."""
    if hasattr(s, 'decode'):
        return s.decode('hex')
    return bytes.fromhex(s)
