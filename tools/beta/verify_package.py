#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline verifier for this beta's RSA/SHA256 AOSP OTA format (stdlib only).

Narrow protocol implementation, not a general certificate/CMS library. Trust is
the release-pinned certificate, not any certificate supplied inside the ZIP.
Format references: AOSP bootable/recovery/otautil/verifier.cpp and
system/update_engine/payload_generator/payload_signer.cc at the release pins.
"""
import base64
import hashlib
import hmac
from pathlib import Path
import struct
import zipfile

import assembly


def require(ok, message):
    if not ok:
        raise ValueError(message)


def der_items(raw):
    """Read bounded, definite-length, single-byte-tag DER elements."""
    require(len(raw) <= 65536, 'Signature structure is too large')
    items = []
    offset = 0
    while offset < len(raw):
        start = offset
        require(offset + 2 <= len(raw), 'Truncated DER')
        tag, size = raw[offset:offset + 2]
        offset += 2
        require(tag & 31 != 31, 'Unsupported DER tag')
        if size & 128:
            count = size & 127
            require(1 <= count <= 4 and offset + count <= len(raw), 'Invalid DER length')
            require(raw[offset] != 0, 'Noncanonical DER length')
            size = int.from_bytes(raw[offset:offset + count], 'big')
            require(size >= 128, 'Noncanonical long DER length')
            offset += count
        require(offset + size <= len(raw), 'Truncated DER value')
        items.append((tag, raw[offset:offset + size], raw[start:offset + size]))
        offset += size
    return items


def one(raw, tag):
    values = der_items(raw)
    require(len(values) == 1 and values[0][0] == tag, 'Unexpected signature structure')
    return values[0][1]


def certificate(pem, expected_der_sha256):
    text = Path(pem).read_text(encoding='ascii')
    body = text.split('-----BEGIN CERTIFICATE-----')[1].split('-----END CERTIFICATE-----')[0]
    der = base64.b64decode(''.join(body.split()), validate=True)
    require(hashlib.sha256(der).hexdigest() == expected_der_sha256, 'Wrong beta signing certificate')
    cert = der_items(one(der, 0x30))
    tbs = der_items(cert[0][1])
    index = 6 if tbs[0][0] == 0xa0 else 5
    require(tbs[index][0] == 0x30, 'Missing certificate public key')
    spki = der_items(tbs[index][1])
    algorithm = der_items(spki[0][1])
    require(algorithm[0][:2] == (6, bytes.fromhex('2a864886f70d010101')), 'Expected RSA public key')
    require(spki[1][0] == 3 and spki[1][1][:1] == b'\0', 'Invalid public key bit string')
    integers = der_items(one(spki[1][1][1:], 0x30))
    require(len(integers) == 2 and all(v[0] == 2 for v in integers), 'Invalid RSA key')
    n, e = (int.from_bytes(v[1], 'big') for v in integers)
    require(2048 <= n.bit_length() <= 8192 and e == 65537, 'Unsupported RSA key')
    return n, e


def verify_rsa(digest, signature, key):
    n, e = key
    size = (n.bit_length() + 7) // 8
    require(len(digest) == 32 and len(signature) == size, 'Wrong RSA signature size')
    value = int.from_bytes(signature, 'big')
    require(value < n, 'Invalid RSA signature integer')
    actual = pow(value, e, n).to_bytes(size, 'big')
    info = bytes.fromhex('3031300d060960864801650304020105000420') + digest
    expected = b'\0\1' + b'\xff' * (size - len(info) - 3) + b'\0' + info
    require(hmac.compare_digest(actual, expected), 'RSA/SHA256 signature verification failed')


def cms_signature(raw):
    content = der_items(one(raw, 0x30))
    require(len(content) == 2 and content[0][:2] == (6, bytes.fromhex('2a864886f70d010702')),
            'Expected CMS SignedData')
    require(content[1][0] == 0xa0, 'Missing CMS content')
    data = der_items(one(content[1][1], 0x30))
    require(len(data) >= 4 and data[-1][0] == 0x31, 'Missing signer information')
    signers = der_items(data[-1][1])
    require(len(signers) == 1 and signers[0][0] == 0x30, 'Expected one beta signer')
    signer = der_items(signers[0][1])
    require([v[0] for v in signer] == [2, 0x30, 0x30, 0x30, 4], 'Unsupported CMS signer format')
    digest_algorithm = der_items(signer[2][1])
    require(digest_algorithm[0][:2] == (6, bytes.fromhex('608648016503040201')),
            'Expected SHA256 CMS signer')
    signature_algorithm = der_items(signer[3][1])
    require(signature_algorithm[0][:2] == (6, bytes.fromhex('2a864886f70d010101')),
            'Expected RSA CMS signer')
    return signer[-1][1]


def hash_ranges(path, ranges):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for offset, length in ranges:
            require(offset >= 0 and length >= 0, 'Invalid signed range')
            source.seek(offset)
            while length:
                chunk = source.read(min(length, 16 * 1024 * 1024))
                require(chunk, 'Truncated signed data')
                result.update(chunk)
                length -= len(chunk)
    return result.digest()


def payload_signature(raw):
    signatures = assembly.fields(raw).get(1, [])
    require(len(signatures) == 1, 'Expected one payload signature')
    value = assembly.fields(signatures[0])
    signature = assembly.single(value, 2, b'')
    size = assembly.single(value, 3)
    if size is not None:
        require(isinstance(size, bytes) and len(size) == 4, 'Invalid signature length')
        size = struct.unpack('<I', size)[0]
        require(0 < size <= len(signature), 'Invalid unpadded signature length')
        require(not any(signature[size:]), 'Unexpected signature padding')
        signature = signature[:size]
    return signature


def verify(path, cert, cert_sha):
    path = Path(path)
    key = certificate(cert, cert_sha)
    size = path.stat().st_size
    require(size >= 28, 'Truncated OTA')
    with path.open('rb') as source:
        source.seek(-6, 2)
        distance, magic, comment_size = struct.unpack('<H2sH', source.read(6))
        require(magic == b'\xff\xff' and 6 < distance <= comment_size, 'Invalid OTA signature footer')
        eocd_size = comment_size + 22
        require(eocd_size <= size, 'Invalid OTA comment length')
        source.seek(size - eocd_size)
        eocd = source.read(eocd_size)
        require(eocd[:4] == b'PK\5\6' and b'PK\5\6' not in eocd[4:], 'Ambiguous ZIP end record')
        require(struct.unpack_from('<H', eocd, 20)[0] == comment_size, 'ZIP comment mismatch')
        source.seek(size - distance)
        signature = cms_signature(source.read(distance - 6))
    verify_rsa(hash_ranges(path, [(0, size - comment_size - 2)]), signature, key)
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo('payload.bin')
        require(info.compress_type == zipfile.ZIP_STORED, 'Expected uncompressed payload')
        props = dict(line.split('=', 1) for line in archive.read('payload_properties.txt').decode().splitlines())
    with path.open('rb') as source:
        source.seek(info.header_offset)
        header = source.read(30)
        require(header[:4] == b'PK\3\4', 'Invalid payload ZIP header')
        names, extra = struct.unpack_from('<HH', header, 26)
        start = info.header_offset + 30 + names + extra
        source.seek(start)
        magic, version, manifest_size, meta_sig_size = struct.unpack('>4sQQI', source.read(24))
        require(magic == b'CrAU' and version == 2 and 0 < manifest_size <= 16 * 1024 * 1024,
                'Unsupported signed payload header')
        require(0 < meta_sig_size <= 65536, 'Invalid metadata signature size')
        metadata_size = 24 + manifest_size
        manifest = assembly.fields(source.read(manifest_size))
        meta_signature = payload_signature(source.read(meta_sig_size))
        offset, length = assembly.single(manifest, 4), assembly.single(manifest, 5)
        require(isinstance(offset, int) and isinstance(length, int) and 0 < length <= 65536,
                'Missing payload signatures')
        sig_start = start + metadata_size + meta_sig_size + offset
        require(sig_start + length == start + info.file_size, 'Invalid payload signature bounds')
        source.seek(sig_start)
        signature = payload_signature(source.read(length))
    metadata_digest = hash_ranges(path, [(start, metadata_size)])
    verify_rsa(metadata_digest, meta_signature, key)
    verify_rsa(hash_ranges(path, [(start, metadata_size),
                                (start + metadata_size + meta_sig_size, offset)]), signature, key)
    require(int(props['FILE_SIZE']) == info.file_size and
            int(props['METADATA_SIZE']) == metadata_size, 'Wrong payload properties size')
    require(base64.b64encode(hash_ranges(path, [(start, info.file_size)])).decode() == props['FILE_HASH'],
            'Payload file hash differs')
    require(base64.b64encode(metadata_digest).decode() ==
            props['METADATA_HASH'], 'Payload metadata hash differs')
    return {'whole_file_RSA_SHA256': True, 'payload_RSA_SHA256': True,
            'metadata_RSA_SHA256': True, 'payload_properties_verified': True}
