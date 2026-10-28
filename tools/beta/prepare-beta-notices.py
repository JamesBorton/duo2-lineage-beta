#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare readable notices and a NEW target-files input for release signing.

Firmware-bearing vendor/ODM images remain unchanged. Existing system-side notice
XML is normalized only for illegal XML control whitespace. Full WebView credits
are recovered from the exact packaged APK, not assigned a Unicode-only license.
"""
import argparse,copy,gzip,hashlib,html,json,re,shutil,struct,subprocess,tempfile,zipfile
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

class Text(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag in ('pre','p','div','h1','h2','h3','br','li'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip-=1
        if tag in ('pre','p','div','h1','h2','h3','li'):self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def sha(data):return hashlib.sha256(data).hexdigest()
def normalize(raw):
    forbidden={code:raw.count(bytes([code])) for code in range(32) if code not in (9,10,13)}
    forbidden={str(k):v for k,v in forbidden.items() if v}
    # These characters are invalid XML; preserve words and represent their layout
    # role with a line break. Original digests/counts remain in the audit report.
    clean=raw.translate(bytes.maketrans(bytes(range(32)),bytes(i if i in (9,10,13) else 10 for i in range(32))))
    return ET.fromstring(clean),forbidden

def webview_credits(apk,host,directory):
    with zipfile.ZipFile(apk) as archive:
        candidates=[name for name in archive.namelist() if 'assets/resources.pak' in name]
        assert len(candidates)==1
        data=archive.read(candidates[0]);assert struct.unpack_from('<I',data)[0]==5
        count=struct.unpack_from('<H',data,8)[0]
        entries=[struct.unpack_from('<HI',data,12+i*6) for i in range(count+1)]
        for i,(ident,offset) in enumerate(entries[:-1]):
            content=data[offset:entries[i+1][1]]
            if not content.startswith(b'\x1e\x9b'):continue
            size=int.from_bytes(content[2:8],'little')
            if size<1000000 or size>64*1024*1024:continue
            compressed=directory/'credits.br';decoded=directory/'credits.html'
            compressed.write_bytes(content[8:])
            subprocess.run([str(host/'brotli'),'-d','-f','-o',str(decoded),str(compressed)],check=True)
            source=decoded.read_bytes();assert len(source)==size
            if b'GNU LESSER GENERAL PUBLIC LICENSE' not in source or b'FFmpeg' not in source:continue
            parser=Text();parser.feed(source.decode('utf-8'))
            text=''.join(parser.parts).strip()+'\n'
            controls={str(i):text.count(chr(i)) for i in range(32) if i not in (9,10,13) and chr(i) in text}
            text=''.join(c if ord(c)>=32 or c in '\t\n\r' else '\n' for c in text)
            assert 'GNU LESSER GENERAL PUBLIC LICENSE' in text and 'FFmpeg' in text
            names=[html.unescape(s.decode()) for s in re.findall(rb'<span class="title">(.*?)</span>',source,re.S)]
            return text,source,{'member':candidates[0],'resource_id':ident,'credits_sha256':sha(source),
                'credits_bytes':len(source),'readable_text_sha256':sha(text.encode()),
                'components':names,'copyright_mentions':text.count('Copyright'),'normalized_layout_controls':controls}
    raise ValueError('Complete embedded WebView license document not found')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-files',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--host-tools',type=Path,required=True)
    parser.add_argument('--webview-source',type=Path,help='Exact original upstream ARM64 prebuilt; replaces a prototype build-resigned APK')
    parser.add_argument('--stock-root',type=Path,required=True,help='Verified owner stock extraction; needed for notices present only inside raw images')
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=False)
    replacements={};report={'input_target_files':args.target_files.name,'partitions':{},'stock_images_changed':False}
    sections=[]
    with zipfile.ZipFile(args.target_files) as archive,tempfile.TemporaryDirectory(prefix='zeta-licenses-') as temporary:
        temp=Path(temporary)
        names=[n for n in archive.namelist() if n.lower().endswith('/webview.apk') and n.startswith(('SYSTEM/','PRODUCT/','SYSTEM_EXT/'))]
        assert len(names)==1,names
        apk=temp/'webview.apk'
        with archive.open(names[0]) as source,apk.open('wb') as destination:shutil.copyfileobj(source,destination,4*1024*1024)
        if args.webview_source:
            upstream=args.webview_source.read_bytes()
            assert sha(upstream)=='1d2f61832b2596b0046cb82cf3634609ea866098d097a83fac27c35272ac726a'
            report['prototype_packaged_webview_sha256']=sha(apk.read_bytes())
            apk.write_bytes(upstream);replacements[names[0]]=upstream
            report['upstream_webview_signature_retained']=True
        badging=subprocess.check_output([str(args.host_tools/'aapt2'),'dump','badging',str(apk)],text=True)
        assert "versionName='156.0.8078.47'" in badging.splitlines()[0],'Update the source/patch lock before accepting another WebView version'
        credits,original,webview=webview_credits(apk,args.host_tools,temp)
        webview.update(apk=names[0],apk_sha256=sha(apk.read_bytes()),
            chromium_version='156.0.8078.47',chromium_commit='1d17a2e2ee147bb7d6ae2ab6abdb3a2510c17775',
            ffmpeg_commit='9db86ce5b5b454dfc96c435f9f0723012980c37f',
            lineage_patches_commit='ef69054c74f7d8306446969136c806738169f1e1',
            prebuilt_commit='5de662a4d42b57a2efe4114e499d38fa3ce41f9d',
            codec_configuration='upstream proprietary_codecs=true, ffmpeg_branding=Chrome; no patent clearance claimed')
        report['webview']=webview
        (args.output_dir/'WebView-Credits.html').write_bytes(original)
        (args.output_dir/'WebView-Credits.txt').write_text(credits)
        sections.append(('WebView and its third-party components',credits))
        inventory=json.loads((args.stock_root/'stock-inventory.json').read_text())
        assert inventory['source_zip_sha256']=='8e695f5e7d4a88ee76d06d4457fd6f203f4c65f35aa0c3e0a87961e24ec5c302'
        for part in ('SYSTEM','SYSTEM_EXT','PRODUCT','VENDOR','ODM'):
            name=part+'/etc/NOTICE.xml.gz'
            origin='target-files'
            if name in archive.namelist():packed=archive.read(name)
            elif part in ('VENDOR','ODM'):
                image=args.stock_root/'images'/(part.lower()+'.img')
                expected=next(p for p in inventory['partitions'] if p['name']==part.lower())
                with image.open('rb') as source:assert hashlib.file_digest(source,'sha256').hexdigest()==expected['sha256']
                result=subprocess.run(['debugfs','-R','cat /etc/NOTICE.xml.gz',str(image)],capture_output=True)
                packed=result.stdout
                if not packed.startswith(b'\x1f\x8b'):continue
                origin='verified stock image, read-only debugfs'
            else:continue
            raw=gzip.decompress(packed)
            try:root,controls=normalize(raw)
            except ET.ParseError as error:
                if part not in ('VENDOR','ODM'):raise
                # The retained OEM XML has additional malformed content beyond
                # control whitespace. Show the entire source as escaped readable
                # text instead of guessing at or dropping any license body.
                text=raw.decode('utf-8','backslashreplace')
                text=''.join(c if ord(c)>=32 or c in '\t\n\r' else '\n' for c in text)
                sections.append((part+' original legal notice (malformed XML; full markup preserved)',text))
                report['partitions'][part]={'original_notice_sha256':sha(packed),'source':origin,
                    'stock_notice_kept_unchanged':True,'parse_error':str(error),
                    'readable_fallback':'complete source text; no license body discarded'}
                continue
            if names[0].startswith(part+'/'):
                content_id=sha(credits.encode())
                ET.SubElement(root,'file-name',{'contentId':content_id}).text='/'+names[0].lower().split('/',1)[0]+'/'+names[0].split('/',1)[1]
                ET.SubElement(root,'file-content',{'contentId':content_id}).text=credits
            contents={n.get('contentId'):n.text or '' for n in root.iter('file-content')}
            filenames={}
            for item in root.iter('file-name'):filenames.setdefault(item.get('contentId'),[]).append(item.text or '')
            for ident,body in contents.items():
                if ident!=sha(credits.encode()):sections.append((part+': '+', '.join(filenames.get(ident,[])),body))
            report['partitions'][part]={'original_notice_sha256':sha(packed),'illegal_control_counts':controls,
                'license_texts':len(contents),'stock_notice_kept_unchanged':part in ('VENDOR','ODM'),'source':origin}
            if part in ('SYSTEM','SYSTEM_EXT','PRODUCT'):
                corrected=ET.tostring(root,encoding='utf-8',xml_declaration=True)
                ET.fromstring(corrected)
                replacements[name]=gzip.compress(corrected,mtime=0)
                report['partitions'][part]['corrected_notice_sha256']=sha(replacements[name])
        bundle=['<!doctype html><meta charset="utf-8"><title>Surface Duo 2 beta notices</title>',
            '<style>body{max-width:1000px;margin:2em auto;padding:1em;font-family:sans-serif}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>',
            '<h1>Surface Duo 2 beta: third-party notices</h1>',
            '<p>Original component terms apply. This document grants no rights to stock firmware. Stock license text is supplied as reference; stock binary inputs come from the device owner.</p>']
        for title,text in sections:bundle.append('<h2>'+html.escape(title)+'</h2><pre>'+html.escape(text)+'</pre>')
        readable='\n'.join(bundle)+'\n'
        (args.output_dir/'NOTICE.html').write_text(readable)
        report['readable_notice_sha256']=sha(readable.encode())
        report['readable_sections']=len(sections)
        report['license_clearance_claimed']=False
        report_data=json.dumps(report,indent=2).encode()+b'\n'
        replacements['META/zeta_notice_corrections.json']=report_data
        output=args.output_dir/'target-files-notices.zip'
        with zipfile.ZipFile(output,'w',allowZip64=True) as destination:
            for info in archive.infolist():
                if info.filename in replacements:
                    destination.writestr(copy.copy(info),replacements.pop(info.filename))
                else:
                    with archive.open(info) as source,destination.open(copy.copy(info),'w') as dest:
                        shutil.copyfileobj(source,dest,4*1024*1024)
            for name,data in replacements.items():destination.writestr(name,data,compress_type=zipfile.ZIP_DEFLATED)
    (args.output_dir/'notice-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'target_files':str(output),'webview_components':len(webview['components']),
        'webview_copyright_mentions':webview['copyright_mentions'],'readable_sections':len(sections),
        'stock_images_changed':False,'license_clearance_claimed':False}),flush=True)

if __name__=='__main__':main()
