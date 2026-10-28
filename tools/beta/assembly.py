#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James Borton and the project contributors.
"""Create or assemble a stock-input beta kit. No network or device operations.

Payload protocol reference: AOSP system/update_engine/update_metadata.proto.
The small wire reader below is project code, not a generated vendor binding.
"""
import argparse
import base64
import bz2
import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import struct
import tempfile
import time
import zipfile

STOCK_SHA256='8e695f5e7d4a88ee76d06d4457fd6f203f4c65f35aa0c3e0a87961e24ec5c302'
PARTS={'vendor','odm','vendor_boot','dtbo'}

def require(value,message):
    if not value:raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as src:return hashlib.file_digest(src,'sha256').hexdigest()

def read_exact(source,count):
    data=source.read(count);require(len(data)==count,'Unexpected end of input');return data

def varint(data,offset):
    result=0
    for shift in range(0,70,7):
        require(offset<len(data),'Truncated protocol integer')
        byte=data[offset];offset+=1;result|=(byte&127)<<shift
        if byte<128:return result,offset
    raise ValueError('Oversized protocol integer')

def fields(data):
    result={};offset=0
    while offset<len(data):
        key,offset=varint(data,offset);number,wire=key>>3,key&7
        require(number>0,'Invalid protocol field')
        if wire==0:value,offset=varint(data,offset)
        elif wire==2:
            size,offset=varint(data,offset);require(size<=len(data)-offset,'Truncated protocol bytes')
            value=data[offset:offset+size];offset+=size
        elif wire in (1,5):
            size=8 if wire==1 else 4;require(offset+size<=len(data),'Truncated fixed field')
            value=data[offset:offset+size];offset+=size
        else:raise ValueError('Unsupported protocol wire type')
        result.setdefault(number,[]).append(value)
    return result

def single(message,key,default=None):
    values=message.get(key,[])
    require(len(values)<=1,'Repeated singular protocol field')
    return values[0] if values else default

def payload(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        info=archive.getinfo('payload.bin')
        require(info.compress_type==zipfile.ZIP_STORED,'Expected stored payload.bin')
    with Path(zip_path).open('rb') as source:
        source.seek(info.header_offset);header=read_exact(source,30)
        require(header[:4]==b'PK\x03\x04','Invalid ZIP local header')
        names,extra=struct.unpack_from('<HH',header,26)
        start=info.header_offset+30+names+extra
        source.seek(start)
        magic,version,size,sigs=struct.unpack('>4sQQI',read_exact(source,24))
        require(magic==b'CrAU' and version==2 and size<=16*1024*1024,'Unsupported payload header')
        manifest=fields(read_exact(source,size))
    block=single(manifest,3,4096)
    require(block==4096 and single(manifest,12,0)==0,'Expected full 4096-byte-block payload')
    parts={}
    for raw in manifest.get(13,[]):
        part=fields(raw);name=single(part,1,b'').decode('ascii')
        require(name and '/' not in name and name not in parts,'Invalid/duplicate partition')
        require(6 not in part,'Incremental stock payload not supported')
        new=fields(single(part,7,b''))
        operations=[]
        for encoded in part.get(8,[]):
            op=fields(encoded);extents=[]
            for extent in op.get(6,[]):
                extent=fields(extent)
                extents.append([single(extent,1,0),single(extent,2,0)])
            operations.append({'type':single(op,1), 'offset':single(op,2,0),
                'length':single(op,3,0),'sha256':single(op,8,b'').hex(),'extents':extents})
        parts[name]={'size':single(new,1),'sha256':single(new,2,b'').hex(),'operations':operations}
    return {'data_start':start+24+size+sigs,'block_size':block,'partitions':parts,'payload_size':info.file_size}

def extract_stock(stock,metadata,destination):
    destination.mkdir(parents=True,exist_ok=False)
    with Path(stock).open('rb') as source:
        for name in sorted(PARTS):
            part=metadata['partitions'][name];path=destination/(name+'.img')
            print('Extracting owner-provided '+name,flush=True)
            with path.open('wb') as image:
                image.truncate(part['size'])
                for op in part['operations']:
                    require(op['type'] in (0,1,6,7,8),'Unsupported stock operation')
                    size=sum(count*4096 for start,count in op['extents'])
                    if op['type'] in (6,7):data=b'\0'*size
                    else:
                        source.seek(metadata['data_start']+op['offset']);packed=read_exact(source,op['length'])
                        require(hashlib.sha256(packed).hexdigest()==op['sha256'],'Stock chunk checksum mismatch')
                        data=bz2.decompress(packed) if op['type']==1 else lzma.decompress(packed) if op['type']==8 else packed
                    require(len(data)==size,'Stock operation size mismatch')
                    cursor=0
                    for start,count in op['extents']:
                        length=count*4096;require((start+count)*4096<=part['size'],'Stock extent outside image')
                        image.seek(start*4096);image.write(data[cursor:cursor+length]);cursor+=length
            require(sha(path)==part['sha256'],'Extracted stock image mismatch: '+name)

def prefix_equal(a,b,size):
    with a.open('rb') as left,b.open('rb') as right:
        while size:
            count=min(size,1024*1024)
            if read_exact(left,count)!=read_exact(right,count):return False
            size-=count
    return True

def image_edits(base,target,minimum):
    require(base.stat().st_size==target.stat().st_size,'Stock image size changed')
    require(prefix_equal(base,target,minimum),'Firmware content changed before AVB metadata')
    result=[];offset=minimum
    with base.open('rb') as a,target.open('rb') as b:
        a.seek(offset);b.seek(offset)
        while old:=a.read(1024*1024):
            new=read_exact(b,len(old))
            if old!=new:
                cursor=0
                while cursor<len(old):
                    if old[cursor]==new[cursor]:cursor+=1;continue
                    start=cursor
                    while cursor<len(old) and old[cursor]!=new[cursor]:cursor+=1
                    result.append({'offset':offset+start,'data':base64.b64encode(new[start:cursor]).decode()})
            offset+=len(old)
    return result

def operation_data(image,extents):
    data=bytearray()
    with image.open('rb') as source:
        for start,count in extents:
            source.seek(start*4096);data.extend(read_exact(source,count*4096))
    return bytes(data)

def copy_bytes(source,destination,offset,length):
    source.seek(offset)
    while length:
        chunk=read_exact(source,min(length,4*1024*1024));destination.write(chunk);length-=len(chunk)

def create(args):
    require(sha(args.stock)==STOCK_SHA256,'Wrong Microsoft recovery ZIP')
    stock=payload(args.stock);current=payload(args.ota)
    require(PARTS<=stock['partitions'].keys() and PARTS<=current['partitions'].keys(),'Missing stock partitions')
    require(not args.output.exists(),'Use a new kit directory')
    # Validate every exclusion/codec before writing a publishable blob.
    lookup={}
    for part in stock['partitions'].values():
        for op in part['operations']:
            if op['length']:lookup.setdefault((op['length'],op['sha256']),stock['data_start']+op['offset'])
    ranges={};partition_specs={}
    for name in sorted(PARTS):
        base=args.stock_images/(name+'.img');target=args.images/(name+'.img')
        old=stock['partitions'][name];new=current['partitions'][name]
        require(base.stat().st_size==old['size'] and sha(base)==old['sha256'],'Unverified stock input: '+name)
        require(target.stat().st_size==new['size'] and sha(target)==new['sha256'],'Target image does not match OTA: '+name)
        with base.open('rb') as stream:
            stream.seek(-64,2);footer=read_exact(stream,64)
        require(footer[:4]==b'AVBf','Missing stock AVB boundary')
        minimum=struct.unpack('>4sIIQQQ28x',footer)[3]
        require(0<minimum<=old['size'],'Invalid firmware boundary')
        edits=image_edits(base,target,minimum)
        if name in ('vendor','odm'):require(not edits and old['sha256']==new['sha256'],'Vendor/ODM must remain byte-identical')
        partition_specs[name]={'size':old['size'],'stock_sha256':old['sha256'],
            'target_sha256':new['sha256'],'firmware_content_bytes':minimum,'metadata_edits':edits}
        for op in new['operations']:
            if not op['length']:continue
            absolute=current['data_start']+op['offset'];key=(op['length'],op['sha256'])
            segment={'offset':absolute,'length':op['length'],'sha256':op['sha256']}
            if key in lookup:segment.update(kind='stock-copy',stock_offset=lookup[key])
            else:
                require(op['type'] in (0,1),'Stock chunk requires nonportable re-encoding; enable the documented ZETA_FULL_REPLACE_BZ2_ONLY=1 host policy')
                segment.update(kind='stock-image',partition=name,codec='bz2' if op['type']==1 else 'raw',extents=op['extents'])
                raw=operation_data(target,op['extents'])
                packed=bz2.compress(raw,compresslevel=9) if op['type']==1 else raw
                require(len(packed)==op['length'] and hashlib.sha256(packed).hexdigest()==op['sha256'],'Non-reproducible stock chunk')
            previous=ranges.setdefault((absolute,op['length']),segment)
            require(previous['sha256']==segment['sha256'],'Conflicting payload range')
    ordered=sorted(ranges.values(),key=lambda row:row['offset'])
    require(all(a['offset']+a['length']<=b['offset'] for a,b in zip(ordered,ordered[1:])),'Overlapping stock ranges')
    args.output.mkdir(parents=True,exist_ok=False)
    segments=[];position=0;literal_position=0
    with args.ota.open('rb') as source,(args.output/'public-data.bin').open('wb') as output:
        for segment in ordered+[{'offset':args.ota.stat().st_size,'length':0}]:
            length=segment['offset']-position
            require(length>=0,'Invalid OTA coverage')
            if length:
                segments.append({'kind':'public','offset':position,'length':length,'data_offset':literal_position})
                copy_bytes(source,output,position,length);literal_position+=length
            if segment['length']:segments.append(segment)
            position=segment['offset']+segment['length']
    manifest={'schema_version':1,'stock_zip_sha256':STOCK_SHA256,'output_name':args.ota.name,
        'output_bytes':args.ota.stat().st_size,'output_sha256':sha(args.ota),
        'public_data_sha256':sha(args.output/'public-data.bin'),'public_data_bytes':literal_position,
        'omitted_stock_payload_bytes':sum(x['length'] for x in ordered),
        'partitions':partition_specs,'segments':segments}
    (args.output/'assembly.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('partitions','segments')}),flush=True)

def assemble(args):
    manifest=json.loads((args.kit/'assembly.json').read_text())
    require(manifest['schema_version']==1 and manifest['stock_zip_sha256']==STOCK_SHA256,'Wrong kit format/base')
    require(not args.output.exists() and not args.output.with_suffix(args.output.suffix+'.partial').exists(),'Output already exists')
    require(sha(args.stock)==STOCK_SHA256,'Wrong or incomplete Microsoft recovery ZIP')
    data=args.kit/'public-data.bin'
    require(data.stat().st_size==manifest['public_data_bytes'] and sha(data)==manifest['public_data_sha256'],'Incomplete or modified beta data')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    required=manifest['output_bytes']+sum(p['size'] for p in manifest['partitions'].values())+1024**3
    require(shutil.disk_usage(args.output.parent).free>=required,'Insufficient temporary disk space')
    partial=args.output.with_suffix(args.output.suffix+'.partial')
    with tempfile.TemporaryDirectory(prefix='duo2-beta-',dir=args.output.parent) as temporary:
        images=Path(temporary)/'images'
        needs_images=any(s['kind']=='stock-image' for s in manifest['segments'])
        if needs_images:
            extract_stock(args.stock,payload(args.stock),images)
            for name,spec in manifest['partitions'].items():
                require(name in PARTS,'Unexpected stock partition')
                image=images/(name+'.img')
                require(sha(image)==spec['stock_sha256'],'Wrong extracted partition')
                with image.open('r+b') as out:
                    for edit in spec['metadata_edits']:
                        blob=base64.b64decode(edit['data'],validate=True);offset=edit['offset']
                        require(offset>=spec['firmware_content_bytes'] and offset+len(blob)<=spec['size'],'Edit touches retained firmware')
                        out.seek(offset);out.write(blob)
                require(sha(image)==spec['target_sha256'],'Reconstructed stock partition mismatch')
        with partial.open('xb') as output,data.open('rb') as literal,args.stock.open('rb') as original:
            for index,segment in enumerate(manifest['segments']):
                require(output.tell()==segment['offset'],'Assembly recipe has a gap or overlap')
                if segment['kind']=='public':
                    copy_bytes(literal,output,segment['data_offset'],segment['length'])
                else:
                    if segment['kind']=='stock-copy':
                        original.seek(segment['stock_offset']);packed=read_exact(original,segment['length'])
                    elif segment['kind']=='stock-image':
                        require(segment['partition'] in PARTS,'Invalid stock partition')
                        raw=operation_data(images/(segment['partition']+'.img'),segment['extents'])
                        require(segment['codec'] in ('bz2','raw'),'Unsupported reconstruction codec')
                        packed=bz2.compress(raw,compresslevel=9) if segment['codec']=='bz2' else raw
                    else:raise ValueError('Unknown recipe segment')
                    require(len(packed)==segment['length'] and hashlib.sha256(packed).hexdigest()==segment['sha256'],'Rebuilt chunk checksum mismatch')
                    output.write(packed)
                if index%100==0:print('Verified assembly segment '+str(index+1)+'/'+str(len(manifest['segments'])),flush=True)
    require(partial.stat().st_size==manifest['output_bytes'] and sha(partial)==manifest['output_sha256'],'Final signed OTA checksum mismatch')
    partial.rename(args.output)
    print('Exact signed OTA reconstructed: '+str(args.output),flush=True)
    print('SHA256 '+manifest['output_sha256'],flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    build=commands.add_parser('create',help='Maintainer: export only non-stock OTA bytes')
    build.add_argument('--ota',type=Path,required=True);build.add_argument('--stock',type=Path,required=True)
    build.add_argument('--images',type=Path,required=True);build.add_argument('--stock-images',type=Path,required=True)
    build.add_argument('--output',type=Path,required=True);build.set_defaults(function=create)
    owner=commands.add_parser('assemble',help='Owner: combine beta data with your official recovery ZIP')
    owner.add_argument('--kit',type=Path,required=True);owner.add_argument('--stock',type=Path,required=True)
    owner.add_argument('--output',type=Path,required=True);owner.set_defaults(function=assemble)
    args=parser.parse_args();started=time.monotonic()
    args.function(args)
    print('Elapsed seconds: '+str(round(time.monotonic()-started,1)),flush=True)

if __name__=='__main__':main()
