#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the source snapshot and detect accidental binary/private material."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def verify(root=ROOT):
    errors = []
    manifest = json.loads((root/'manifests/source-snapshot.json').read_text())
    projects = manifest['projects']
    if len(projects) != 6:
        errors.append('Expected six source projects')
    omitted = manifest.get('retired_contracts', [])
    if len(omitted) != 4:
        errors.append('Expected four explicitly retired contracts')
    checked = 0
    for name, entry in manifest['source_files'].items():
        path = root/name
        if not path.is_file() or path.is_symlink():
            errors.append('Missing or linked source: '+name)
            continue
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if hashlib.sha256(data).hexdigest() != entry['sha256'] or blob != entry['git_blob']:
            errors.append('Source integrity mismatch: '+name)
        checked += 1
    for spec in projects:
        if 'patch' not in spec:
            continue
        path = root/spec['patch']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=spec['patch_sha256']:
            errors.append('Patch integrity mismatch: '+spec['id'])
    forbidden_extensions = {'.apk','.apex','.img','.ko','.so','.p12','.pfx','.jks','.keystore','.key','.zip','.7z','.bundle','.exe','.dll'}
    sensitive = [
        rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
        rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',
        rb'\bAKIA[A-Z0-9]{16}\b',
        rb'\b0F[0-9A-Z]{11,}\b',
        rb'\b10\.254\.\d+\.\d+\b',
        rb'(?:/mnt/c/Users/|C:[/\\]Users[/\\])james\b',
    ]
    paths = []
    if (root/'.git').exists():
        paths = [root/p.decode() for p in subprocess.check_output(['git','-C',str(root),'ls-files','-z']).split(b'\0') if p]
    else:
        paths = [p for p in root.rglob('*') if p.is_file()]
    for path in paths:
        name = path.relative_to(root).as_posix()
        if path.is_symlink() or path.suffix.lower() in forbidden_extensions:
            errors.append('Excluded file type: '+name)
            continue
        if path.suffix.lower() == '.hal':
            errors.append('Excluded third-party contract: '+name)
        data = path.read_bytes()
        if path.suffix == '.gz':
            if name != 'patches/kernel-sm8350.patch.gz':
                errors.append('Unreviewed compressed payload: '+name)
                continue
            data = gzip.decompress(data)
        if b'\0' in data or (b'GIT '+b'binary patch') in data:
            errors.append('Unexpected binary content: '+name)
        for pattern in sensitive:
            if re.search(pattern, data):
                errors.append('Potential private material (inspect locally): '+name)
                break
    from xml.etree import ElementTree as ET
    lock = ET.parse(root/'manifests/upstream.xml').getroot()
    for remote in lock.findall('remote'):
        if not remote.get('fetch','').startswith('https://'):
            errors.append('Non-public manifest remote')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'result':'PASS','source_files':checked,'projects':len(projects),
                      'retired_contracts':len(omitted),'files_scanned':len(paths),
                      'scope':'source hashes and heuristic privacy/binary checks; not legal or hardware clearance'}))

if __name__ == '__main__':
    verify()
