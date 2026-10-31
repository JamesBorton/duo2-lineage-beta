# SPDX-License-Identifier: Apache-2.0
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import verify_package as crypto

class SignatureRejectionTests(unittest.TestCase):
    def test_truncated_noncanonical_and_indefinite_der(self):
        for raw in [b'\x30', b'\x30\x80', b'\x30\x81\x01x', b'\x30\x82\0\x80', b'\x30\x05x']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):crypto.der_items(raw)

    def test_wrong_rsa_signature_rejected(self):
        with self.assertRaises(ValueError):crypto.verify_rsa(b'0'*32,b'0'*256,((1<<2048)-159,65537))

    def test_wrong_signature_integer_rejected(self):
        with self.assertRaises(ValueError):crypto.verify_rsa(b'0'*32,b'\xff'*256,((1<<2048)-159,65537))

    def test_unsupported_cms_rejected(self):
        for raw in [b'\x30\0',b'garbage',b'\x30\2\x06\0']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):crypto.cms_signature(raw)


if __name__ == '__main__':unittest.main()
