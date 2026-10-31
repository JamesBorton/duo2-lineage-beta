#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create an owner-authorized temporary recovery; no device commands or private keys.

Requires the exact normal boot image, stock build facts and recovery-layout recipe
published with a verified release. Output is for fastboot boot on an unlocked
Surface Duo 2 only. It is never an OTA boot replacement or a relocking image.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import shutil
import os


def require(condition,message):
    if not condition:raise ValueError(message)


def unpack_cpio(raw):
    entries=[];offset=0
    while True:
        header=raw[offset:offset+110]
        require(header[:6] in (b'070701',b'070702'),'Expected newc ramdisk')
        fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
        offset+=110
        require(0<fields[11]<=4096,'Invalid ramdisk filename')
        name=raw[offset:offset+fields[11]-1].decode()
        require(not name.startswith('/') and '..' not in name.split('/'),'Unsafe ramdisk path')
        offset=(offset+fields[11]+3)&~3
        data=raw[offset:offset+fields[6]]
        require(len(data)==fields[6],'Truncated ramdisk')
        offset=(offset+fields[6]+3)&~3
        if name=='TRAILER!!!':break
        entries.append((name.removeprefix('./'),fields,data))
    groups={(f[0],f[7],f[8]):data for _,f,data in entries if f[1]&0o170000==0o100000 and data}
    return [(name,f,groups.get((f[0],f[7],f[8]),data) if f[1]&0o170000==0o100000 and f[4]>1 else data) for name,f,data in entries]


def pack_cpio(entries):
    output=bytearray()
    for inode,(name,fields,data) in enumerate(entries+[('TRAILER!!!',[0]*13,b'')],1):
        f=list(fields);f[0]=inode;f[4]=1;f[6]=len(data);f[11]=len(name.encode())+1;f[12]=0
        output.extend(b'070701'+b''.join(f'{n:08x}'.encode() for n in f))
        output.extend(name.encode()+b'\0');output.extend(b'\0'*((-len(output))%4))
        output.extend(data);output.extend(b'\0'*((-len(output))%4))
    output.extend(b'\0'*((-len(output))%512))
    return bytes(output)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--boot',type=Path,required=True)
    ap.add_argument('--recipe',type=Path,required=True)
    ap.add_argument('--adb-public-key',type=Path,required=True,help='Existing platform-tools adbkey.pub, never adbkey')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    require(not args.output.exists(),'Output already exists')
    recipe=json.loads(args.recipe.read_text())
    source=args.boot.read_bytes()
    require(hashlib.sha256(source).hexdigest()==recipe['source_boot_sha256'],'Wrong normal boot image')
    require(source[:8]==b'ANDROID!' and struct.unpack_from('<I',source,40)[0]==3,'Expected boot header v3')
    kernel_size,ramdisk_size=struct.unpack_from('<II',source,8)
    page=4096;ramdisk_offset=page+((kernel_size+page-1)//page)*page
    kernel=source[page:page+kernel_size]
    require(hashlib.sha256(kernel).hexdigest()==recipe['kernel_sha256'],'Wrong kernel')
    packed=source[ramdisk_offset:ramdisk_offset+ramdisk_size]
    require(packed.startswith(b'\x1f\x8b'),'Expected release gzip ramdisk')
    entries=unpack_cpio(gzip.decompress(packed))
    require(not any(n.startswith('first_stage_ramdisk/system/bin/recovery') for n,_,_ in entries),'Input is already a temporary recovery')
    key=args.adb_public_key.read_text().split()[0]
    require(len(base64.b64decode(key,validate=True))==524,'Expected Android RSA adbkey.pub')
    adb=(key+'\n').encode()
    original={n:data for n,_,data in entries}
    props=dict(line.split('=',1) for line in original['prop.default'].decode().splitlines() if '=' in line and not line.startswith('#'))
    require(props.get('ro.adb.secure')=='1' and props.get('ro.adb.secure.recovery','1')=='1','Secure ADB must remain enabled')
    require(not original.get('adb_keys',b'').strip(),'Release input contains pre-authorized ADB keys')
    normalized=[]
    for name,f,data in entries:
        if name=='adb_keys':continue
        if name=='prop.default':
            facts=recipe['stock_build_properties']
            lines=[];seen=set()
            for line in data.decode().splitlines():
                key_name=line.partition('=')[0]
                if key_name.startswith(('ro.vendor.build.','ro.odm.build.')):
                    if key_name in facts:lines.append(key_name+'='+facts[key_name]);seen.add(key_name)
                else:lines.append(line)
            lines += [k+'='+v for k,v in sorted(facts.items()) if k not in seen]
            data=('\n'.join(lines)+'\n').encode()
        elif name=='init.recovery.surfaceduo2.rc':
            text=data.decode();needle='    setprop sys.usb.configfs 1'
            require(text.count(needle)==1,'Unknown recovery USB setup')
            text=text.replace(needle,needle+'\n    setprop sys.usb.controller a600000.dwc3\n    write /sys/class/udc/a600000.dwc3/device/../mode peripheral',1)
            text+='\n# USB2 transport and slot HAL for temporary installer.\non post-fs\n    write /config/usb_gadget/g1/max_speed high-speed\n    write /config/usb_gadget/g1/configs/b.1/MaxPower 500\n\non boot\n    start vendor.boot-qti\n\non post-fs\n    restorecon /adb_keys\n'
            data=text.encode()
        elif name=='system/etc/init/hw/init.rc':
            needle=b'import /init.recovery.${ro.hardware}.rc'
            require(data.count(needle)==1,'Unknown recovery init import')
            data=data.replace(needle,b'import /init.recovery.surfaceduo2.rc')
        normalized.append((name,f,data))
    fields=list(next(f for name,f,_ in normalized if name=='prop.default'))
    fields[1]=0o100644;fields[2]=0;fields[3]=0;fields[4]=1
    normalized.append(('adb_keys',fields,adb))
    required=('init','system/bin/init','system/bin/recovery','system/bin/adbd','sepolicy','system/bin/zeta-slot-status','system/bin/update_engine_sideload','system/bin/hw/android.hardware.boot-service.qti.recovery')
    after={n:data for n,_,data in normalized}
    for name in required:require(after.get(name)==original.get(name) and name in after,'Recovery binary/policy changed or missing: '+name)
    mirrored=[('first_stage_ramdisk/'+name,f,data) for name,f,data in normalized if name not in ('','.','first_stage_ramdisk') and not name.startswith('first_stage_ramdisk/')]
    ramdisk=bytearray(gzip.compress(pack_cpio(normalized+mirrored),compresslevel=9,mtime=0))
    ramdisk[9]=255  # Canonical gzip OS byte across Python 3.11-3.13 and hosts.
    ramdisk=bytes(ramdisk)
    header=bytearray(source[:page]);struct.pack_into('<I',header,12,len(ramdisk))
    image=bytes(header)+source[page:ramdisk_offset]+ramdisk
    image+=b'\0'*((-len(image))%page)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    avbtool=Path(__file__).resolve().parent/'third_party/avbtool.py'
    # AVB resolves a hash descriptor by partition name, so verify a staged
    # boot.img even when the owner chooses another output filename.
    child_env = {k:v for k,v in os.environ.items() if not k.upper().startswith('PYTHON') and k.upper() not in ('AVB_INVOCATION_LOGFILE','ANDROID_SECURE_STORAGE_CMD','TMP__KEY_FILE_NAME')}
    with tempfile.TemporaryDirectory(prefix='zeta-recovery-',dir=args.output.parent) as scratch:
        staged=Path(scratch)/'boot.img';staged.write_bytes(image)
        subprocess.run([sys.executable,'-I',str(avbtool),'add_hash_footer','--image',str(staged),'--partition_name','boot',
                        '--partition_size','134217728','--salt','00'*32],check=True,env=child_env)
        subprocess.run([sys.executable,'-I',str(avbtool),'verify_image','--image',str(staged)],check=True,env=child_env)
        with staged.open('rb') as src,args.output.open('xb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
    with args.output.open('rb') as out:digest=hashlib.file_digest(out,'sha256').hexdigest()
    print('Temporary owner-authorized recovery prepared:',args.output)
    print('SHA256',digest)
    print('Use only with the matching tested release instructions. No phone command was executed.')


if __name__=='__main__':main()
