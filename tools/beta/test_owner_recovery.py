#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Portable recovery framing, trust and preservation tests; no phone operations."""
import base64,gzip,hashlib,importlib.util,json
from pathlib import Path
import struct,subprocess,sys,tempfile,unittest,os
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare_owner_recovery',ROOT/'prepare-owner-recovery.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        fields=[1,0o100644,0,0,1,0,0,0,0,0,0,0,0]
        names=('init','system/bin/init','system/bin/recovery','system/bin/adbd','sepolicy','system/bin/zeta-slot-status','system/bin/update_engine_sideload','system/bin/hw/android.hardware.boot-service.qti.recovery')
        self.entries=[(name,fields,b'fixture:'+name.encode()) for name in names]
        self.entries += [('prop.default',fields,b'ro.adb.secure=1\nro.adb.secure.recovery=1\n'),('adb_keys',fields,b''),
            ('init.recovery.surfaceduo2.rc',fields,b'on init\n    setprop sys.usb.configfs 1\n'),
            ('system/etc/init/hw/init.rc',fields,b'import /init.recovery.${ro.hardware}.rc\n')]
        self.kernel=b'fixture-kernel'*1024
        self.boot=self.root/'normal.img';self.recipe=self.root/'recipe.json';self.key=self.root/'adbkey.pub';self.output=self.root/'temporary.img'
        self.key.write_text(base64.b64encode(b'K'*524).decode()+' owner-fixture\n')
        self.write_input()

    def tearDown(self):self.temp.cleanup()

    def write_input(self):
        ramdisk=gzip.compress(module.pack_cpio(self.entries),mtime=0)
        header=bytearray(4096);header[:8]=b'ANDROID!';struct.pack_into('<IIII',header,8,len(self.kernel),len(ramdisk),0,1580);struct.pack_into('<I',header,40,3)
        kernel=self.kernel+b'\0'*((-len(self.kernel))%4096)
        image=bytes(header)+kernel+ramdisk
        self.boot.write_bytes(image)
        self.recipe.write_text(json.dumps({'source_boot_sha256':hashlib.sha256(image).hexdigest(),
            'kernel_sha256':hashlib.sha256(self.kernel).hexdigest(),'stock_build_properties':{'ro.vendor.build.date.utc':'1725862109','ro.odm.build.date.utc':'1725862109'}}))

    def run_tool(self):
        return subprocess.run([sys.executable,str(ROOT/'prepare-owner-recovery.py'),'--boot',str(self.boot),'--recipe',str(self.recipe),
            '--adb-public-key',str(self.key),'--output',str(self.output)],capture_output=True,text=True)

    def test_preserves_kernel_binaries_and_secure_owner_trust(self):
        r=self.run_tool();self.assertEqual(r.returncode,0,r.stderr)
        data=self.output.read_bytes();self.assertEqual(len(data),134217728)
        self.assertEqual(data[4096:4096+len(self.kernel)],self.kernel)
        offset=4096+((len(self.kernel)+4095)//4096)*4096
        size=struct.unpack_from('<I',data,12)[0]
        entries={name:body for name,_,body in module.unpack_cpio(gzip.decompress(data[offset:offset+size]))}
        self.assertEqual(entries['adb_keys'],self.key.read_text().split()[0].encode()+b'\n')
        self.assertEqual(entries['first_stage_ramdisk/adb_keys'],entries['adb_keys'])
        self.assertIn(b'ro.adb.secure=1',entries['prop.default'])
        for name,_,body in self.entries:
            if name.startswith('system/bin/') or name in ('init','sepolicy'):
                self.assertEqual(entries[name],body);self.assertEqual(entries['first_stage_ramdisk/'+name],body)

    def test_inherited_avb_logging_hook_cannot_write_a_file(self):
        unwanted=self.root/'unrequested-log'
        with patch.dict(os.environ, {'AVB_INVOCATION_LOGFILE':str(unwanted),
                                   'ANDROID_SECURE_STORAGE_CMD':'must-not-run'}):
            result=self.run_tool()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(unwanted.exists())

    def test_wrong_input_rejected(self):
        self.boot.write_bytes(self.boot.read_bytes()+b'changed')
        self.assertNotEqual(self.run_tool().returncode,0);self.assertFalse(self.output.exists())

    def test_foreign_adb_key_rejected(self):
        self.entries=[(n,f,b'foreign-key' if n=='adb_keys' else b) for n,f,b in self.entries];self.write_input()
        self.assertNotEqual(self.run_tool().returncode,0);self.assertFalse(self.output.exists())

    def test_insecure_adb_rejected(self):
        self.entries=[(n,f,b'ro.adb.secure=0\n' if n=='prop.default' else b) for n,f,b in self.entries];self.write_input()
        self.assertNotEqual(self.run_tool().returncode,0);self.assertFalse(self.output.exists())

    def test_existing_output_preserved(self):
        self.output.write_bytes(b'preserve');self.assertNotEqual(self.run_tool().returncode,0);self.assertEqual(self.output.read_bytes(),b'preserve')

if __name__=='__main__':unittest.main()
