from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from unittest import TestCase
from pymidi import utils


class UtilsTests(TestCase):
    def test_is_ipv4_address(self):
        bad_ips = ['hello', '', None, object]
        for ip in bad_ips:
            self.assertEqual(False, utils.is_ipv4_address(ip),
                'Expected {} to return False'.format(repr(ip)))

        good_ips = ['127.0.0.1', '8.8.8.8']
        for ip in good_ips:
            self.assertEqual(True, utils.is_ipv4_address(ip),
                'Expected {} to return True'.format(repr(ip)))

    def test_is_ipv6_address(self):
        bad_ips = ['hello', '', None, object]
        for ip in bad_ips:
            self.assertEqual(False, utils.is_ipv6_address(ip),
                'Expected {} to return False'.format(repr(ip)))

        good_ips = ['::', '2001:0db8:85a3:0000:0000:8a2e:0370:7334']
        for ip in good_ips:
            self.assertEqual(True, utils.is_ipv6_address(ip),
                'Expected {} to return True'.format(repr(ip)))

    def test_validate_addr(self):
        bad_addrs = [None, ('boom', 'dip'), ('', 80), ('localhost', 80)]
        for addr in bad_addrs:
            with self.assertRaises(ValueError):
                utils.validate_addr(addr)

        good_addrs = [('127.0.0.1', 80), ('8.8.8.8', 2048), ('::', 5051)]
        for addr in good_addrs:
            utils.validate_addr(addr)

    def test_b2h(self):
        mybytes = b'yo'
        self.assertEqual('796f', utils.b2h(mybytes))
        mybytes = b'\xfe\xed\xfa\xce'
        self.assertEqual('feedface', utils.b2h(mybytes))
