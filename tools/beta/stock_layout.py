# SPDX-License-Identifier: Apache-2.0
"""Read-only single-super LP metadata/prefix hashing, following AOSP liblp.

Does not create mappings, mount filesystems, or write partition metadata.
Unsupported/corrupt layouts fail closed before the first-install erase step.
"""
import hashlib
import re
import struct


def need(ok, message):
    if not ok:
        raise ValueError(message)


def name(raw):
    text = raw.split(b'\0', 1)[0].decode('ascii')
    # Virtual A/B metadata can retain names such as vendor_a-cow. Names are
    # never executed or used as a device path; only fixed vendor/odm source
    # names and the exact physical device name "super" are selected below.
    need(re.fullmatch('[A-Za-z0-9_-]+', text), 'Invalid LP partition name')
    return text


def geometry(raw):
    need(len(raw) == 52, 'Truncated LP geometry')
    magic, size = struct.unpack_from('<II', raw)
    need(magic == 0x616c4467 and size == 52, 'Unsupported LP geometry')
    need(hashlib.sha256(raw[:8] + b'\0' * 32 + raw[40:]).digest() == raw[8:40], 'Bad LP geometry checksum')
    maximum, slots, block = struct.unpack_from('<III', raw, 40)
    need(4096 <= maximum <= 16 * 1024 * 1024 and maximum % 512 == 0 and
         slots in (2, 3) and block == 4096, 'Unsupported Duo 2 LP geometry')
    return maximum, slots


def inspect(reader, physical_size, slot):
    """reader(offset,length) returns exact bytes from the physical super device."""
    need(slot in ('a', 'b') and physical_size >= 4096 * 4, 'Invalid super/source slot')
    primary, backup = reader(4096, 52), reader(8192, 52)
    maximum, slots = geometry(primary)
    need(primary == backup, 'LP geometry copies disagree')
    offset = 12288 + (0 if slot == 'a' else 1) * maximum
    need(offset + maximum <= physical_size, 'LP metadata exceeds super')
    raw = reader(offset, maximum)
    need(len(raw) == maximum and len(raw) >= 128, 'Truncated LP metadata')
    magic, major, minor, header_size = struct.unpack_from('<IHHI', raw)
    need(magic == 0x414c5030 and major == 10 and minor in (0, 1, 2) and
         header_size == (256 if minor == 2 else 128), 'Unsupported LP metadata version')
    need(hashlib.sha256(raw[:12] + b'\0' * 32 + raw[44:header_size]).digest() == raw[12:44], 'Bad LP header checksum')
    table_size = struct.unpack_from('<I', raw, 44)[0]
    need(header_size + table_size <= len(raw), 'LP tables exceed metadata')
    tables = raw[header_size:header_size + table_size]
    need(hashlib.sha256(tables).digest() == raw[48:80], 'Bad LP table checksum')
    if header_size == 256:
        need(not struct.unpack_from('<I', raw, 128)[0] & 2, 'Remount overlays are unsupported')
    def table(at, entry_size):
        start, count, size = struct.unpack_from('<III', raw, at)
        need(size == entry_size and count <= 65536 and start + count * size <= len(tables), 'Invalid LP table bounds')
        return [tables[start + i * size:start + (i + 1) * size] for i in range(count)]
    partitions, extents, groups, devices = table(80, 52), table(92, 24), table(104, 48), table(116, 64)
    need(len(devices) == 1 and name(devices[0][24:60]) == 'super', 'Only the physical super device is supported')
    first = struct.unpack_from('<Q', devices[0])[0] * 512
    declared = struct.unpack_from('<Q', devices[0], 16)[0]
    need(declared == physical_size and 12288 + 2 * maximum * slots <= first < physical_size,
         'Physical super size/usable range differs')
    result = {}
    for part in partitions:
        label = name(part[:36])
        need(label not in result, 'Duplicate LP partition')
        attributes, first_extent, count, group = struct.unpack_from('<IIII', part, 36)
        need(group < len(groups) and first_extent + count <= len(extents), 'Invalid LP partition extent range')
        ranges = []
        for extent in extents[first_extent:first_extent + count]:
            sectors, kind, sector, source = struct.unpack('<QIQI', extent)
            length = sectors * 512
            need(length > 0 and length % 4096 == 0, 'Invalid logical extent size')
            if kind == 0:
                need(source == 0 and sector * 512 >= first and sector * 512 + length <= physical_size,
                     'LP extent escapes physical super')
                ranges.append((sector * 512, length))
            else:
                need(kind == 1 and sector == 0 and source == 0, 'Unsupported LP target')
                ranges.append((None, length))
        result[label] = ranges
    need(all(n + '_' + slot in result for n in ('vendor', 'odm')), 'Source vendor/ODM mappings are absent')
    return result


def prefix_hash(reader, ranges, length):
    need(0 < length <= sum(size for _, size in ranges), 'Stock image exceeds its logical partition')
    digest = hashlib.sha256()
    remaining = length
    for offset, available in ranges:
        take = min(remaining, available)
        done = 0
        while done < take:
            count = min(take - done, 8 * 1024 * 1024)
            data = b'\0' * count if offset is None else reader(offset + done, count)
            need(len(data) == count, 'Short read from stock logical partition')
            digest.update(data)
            done += count
        remaining -= take
        if not remaining:
            break
    need(remaining == 0, 'Incomplete stock prefix')
    return digest.hexdigest()
