#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic reconstruction and rejection tests; includes no real firmware."""
import argparse
import bz2
import contextlib
import hashlib
import importlib.util
import io
import lzma
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
MODULE=HERE/'assembly.py'
spec=importlib.util.spec_from_file_location('beta_assembly',MODULE)
beta=importlib.util.module_from_spec(spec);spec.loader.exec_module(beta)

def integer(value):
    result=bytearray()
    while value>=128:result.append((value&127)|128);value>>=7
    result.append(value);return bytes(result)

def field(number,value):
    return integer(number<<3)+integer(value) if isinstance(value,int) else integer((number<<3)|2)+integer(len(value))+value

def make_zip(path,images,xz=False):
    blob=bytearray();partitions=[]
    for name,image in images.items():
        packed=lzma.compress(image) if xz else bz2.compress(image,compresslevel=9)
        op=(field(1,8 if xz else 1)+field(2,len(blob))+field(3,len(packed))+
            field(6,field(1,0)+field(2,len(image)//4096))+field(8,hashlib.sha256(packed).digest()))
        info=field(1,len(image))+field(2,hashlib.sha256(image).digest())
        partitions.append(field(13,field(1,name.encode())+field(7,info)+field(8,op)))
        blob.extend(packed)
    manifest=field(3,4096)+field(12,0)+b''.join(partitions)
    payload=struct.pack('>4sQQI',b'CrAU',2,len(manifest),0)+manifest+blob
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as output:
        output.writestr('payload.bin',payload)
        output.writestr('metadata.txt','synthetic test data, not an installable ROM')
    with path.open('ab') as output:output.write(b'EXACT-TRAILING-SIGNATURE-BYTES-TEST')

class AssemblyTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='duo2-assembly-test-')
        self.root=Path(self.temporary.name)
        self.stock_images=self.root/'stock-images';self.stock_images.mkdir()
        self.images=self.root/'images';self.images.mkdir()
        old={};new={}
        for name in sorted(beta.PARTS):
            image=bytearray(65536)
            marker=('SYNTHETIC-OEM-FIRMWARE-MARKER-'+name).encode()
            image[:8192]=(marker*((8192//len(marker))+1))[:8192]
            image[32768:32776]=b'OLD-META'
            image[-64:]=struct.pack('>4sIIQQQ28x',b'AVBf',1,0,8192,32768,256)
            old[name]=bytes(image)
            if name in ('dtbo','vendor_boot'):image[32768:32776]=b'NEW-META'
            new[name]=bytes(image)
            (self.stock_images/(name+'.img')).write_bytes(old[name])
            (self.images/(name+'.img')).write_bytes(new[name])
        new['system']=(b'PROJECT-OWNED-TEST-CONTENT'*3000)[:65536]
        self.stock=self.root/'stock.zip';self.ota=self.root/'candidate.zip'
        make_zip(self.stock,old);make_zip(self.ota,new)
        beta.STOCK_SHA256=beta.sha(self.stock)
        self.new_images=new
        self.kit=self.root/'kit'
        self.create_args=argparse.Namespace(stock=self.stock,ota=self.ota,images=self.images,
            stock_images=self.stock_images,output=self.kit)
    def tearDown(self):self.temporary.cleanup()
    def create(self):
        with contextlib.redirect_stdout(io.StringIO()):beta.create(self.create_args)
    def assemble(self,output=None):
        args=argparse.Namespace(stock=self.stock,kit=self.kit,output=output or self.root/'rebuilt.zip')
        with contextlib.redirect_stdout(io.StringIO()):beta.assemble(args)
        return args.output
    def test_rebuild_is_byte_identical_with_copy_and_regenerated_chunks(self):
        self.create();result=self.assemble()
        self.assertEqual(result.read_bytes(),self.ota.read_bytes())
        self.assertNotIn(b'SYNTHETIC-OEM-FIRMWARE-MARKER',(self.kit/'public-data.bin').read_bytes())
        manifest=__import__('json').loads((self.kit/'assembly.json').read_text())
        kinds={x['kind'] for x in manifest['segments']}
        self.assertEqual(kinds,{'public','stock-copy','stock-image'})
        for part in manifest['partitions'].values():
            self.assertTrue(all(edit['offset']>=8192 for edit in part['metadata_edits']))
    def test_wrong_stock_is_rejected_before_output(self):
        self.create();self.stock.write_bytes(b'wrong input')
        with self.assertRaises(ValueError):self.assemble()
        self.assertFalse((self.root/'rebuilt.zip').exists())
    def test_modified_public_data_is_rejected(self):
        self.create();path=self.kit/'public-data.bin'
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaises(ValueError):self.assemble()
    def test_original_firmware_changes_are_rejected(self):
        image=bytearray((self.images/'dtbo.img').read_bytes());image[10]^=1
        (self.images/'dtbo.img').write_bytes(image);self.new_images['dtbo']=bytes(image)
        make_zip(self.ota,self.new_images)
        with self.assertRaises(ValueError):self.create()
        self.assertFalse(self.kit.exists())
    def test_nonportable_unmatched_xz_is_rejected(self):
        make_zip(self.ota,self.new_images,xz=True)
        with self.assertRaisesRegex(ValueError,'nonportable'):self.create()
        self.assertFalse(self.kit.exists())
    def test_existing_output_is_never_overwritten(self):
        self.create();output=self.root/'keep.zip';output.write_bytes(b'keep')
        with self.assertRaises(ValueError):self.assemble(output)
        self.assertEqual(output.read_bytes(),b'keep')
    def test_truncated_protocol_is_rejected(self):
        with self.assertRaises(ValueError):beta.fields(b'\x82')
        with self.assertRaises(ValueError):beta.fields(b'\x0a\x06abc')
    def test_stock_decoder_reconstructs_exact_images(self):
        dest=self.root/'extracted'
        with contextlib.redirect_stdout(io.StringIO()):beta.extract_stock(self.stock,beta.payload(self.stock),dest)
        for name in beta.PARTS:
            self.assertEqual((dest/(name+'.img')).read_bytes(),(self.stock_images/(name+'.img')).read_bytes())

if __name__=='__main__':unittest.main()
