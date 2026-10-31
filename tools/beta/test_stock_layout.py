# SPDX-License-Identifier: Apache-2.0
import hashlib
import struct
import unittest

import stock_layout as lp


def fixed(value, count=36): return value.encode().ljust(count, b'\0')


def fixture(bad_source=False, duplicate=False, overlay=False):
    total=65536;disk=bytearray(total);maximum=4096;slots=2
    geometry=bytearray(struct.pack('<II32sIII',0x616c4467,52,b'\0'*32,maximum,slots,4096))
    geometry[8:40]=hashlib.sha256(geometry).digest()
    disk[4096:4096+52]=geometry;disk[8192:8192+52]=geometry
    parts=[];extents=[]
    for index,label in enumerate(['vendor_a','odm_a','vendor_b','odm_b']):
        if duplicate and index==1:label='vendor_a'
        parts.append(fixed(label)+struct.pack('<IIII',1,index,1,0))
        extents.append(struct.pack('<QIQI',8,0,64+index*8,1 if bad_source else 0))
        disk[32768+index*4096:32768+(index+1)*4096]=bytes([65+index])*4096
    blocks=[b''.join(parts),b''.join(extents),fixed('default')+struct.pack('<IQ',0,0),
            struct.pack('<QIIQ',64,4096,0,total)+fixed('super')+struct.pack('<I',0)]
    tables=b''.join(blocks);header=bytearray(256 if overlay else 128)
    struct.pack_into('<IHHI',header,0,0x414c5030,10,2 if overlay else 0,len(header))
    struct.pack_into('<I',header,44,len(tables));header[48:80]=hashlib.sha256(tables).digest()
    start=0
    for at,block,size in zip([80,92,104,116],blocks,[52,24,48,64]):
        struct.pack_into('<III',header,at,start,len(block)//size,size);start+=len(block)
    if overlay:struct.pack_into('<I',header,128,2)
    header[12:44]=hashlib.sha256(header).digest()
    for index in range(2):disk[12288+index*maximum:12288+index*maximum+len(header)+len(tables)]=header+tables
    return disk


class LayoutTests(unittest.TestCase):
    def test_both_slots_use_their_correct_logical_extents(self):
        disk=fixture();reader=lambda o,n:bytes(disk[o:o+n])
        for slot,byte in [('a',b'A'),('b',b'C')]:
            mappings=lp.inspect(reader,len(disk),slot)
            self.assertEqual(lp.prefix_hash(reader,mappings['vendor_'+slot],4096),hashlib.sha256(byte*4096).hexdigest())

    def test_geometry_checksum_failure(self):
        disk=fixture();disk[4100]^=1
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk),'a')

    def test_disagreeing_geometry(self):
        disk=fixture();disk[8192+8]^=1
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk),'a')

    def test_table_checksum_failure(self):
        disk=fixture();disk[12288+140]^=1
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk),'a')

    def test_wrong_physical_partition_size(self):
        disk=fixture()
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk)+4096,'a')

    def test_cannot_read_another_physical_device(self):
        disk=fixture(bad_source=True)
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk),'a')

    def test_duplicate_partition_rejected(self):
        disk=fixture(duplicate=True)
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk),'a')

    def test_overlay_rejected(self):
        disk=fixture(overlay=True)
        with self.assertRaises(ValueError):lp.inspect(lambda o,n:bytes(disk[o:o+n]),len(disk),'a')

    def test_zero_extent_and_noncontiguous_ranges(self):
        raw=b'A'*4096+b'B'*4096
        self.assertEqual(lp.prefix_hash(lambda o,n:raw[o:o+n],[(4096,4096),(None,4096),(0,4096)],12288),
                         hashlib.sha256(b'B'*4096+b'\0'*4096+b'A'*4096).hexdigest())

    def test_short_read_and_oversized_prefix_rejected(self):
        for ranges,size in [([(0,4096)],8192), ([(0,4096)],4096)]:
            with self.assertRaises(ValueError):lp.prefix_hash(lambda o,n:b'',ranges,size)


if __name__=='__main__':unittest.main()
