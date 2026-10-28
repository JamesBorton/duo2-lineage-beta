#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Restore reviewed source into NEW directories. No builds or device operations."""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def git(repo, *args, data=None):
    return subprocess.check_output(['git','-C',str(repo),*args],input=data)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--upstream-cache',type=Path,help='Optional existing source checkout, used only to fetch exact public bases')
    args = parser.parse_args()
    subprocess.run([sys.executable,str(ROOT/'tools/verify-public-tree.py')],check=True)
    dest = args.destination.resolve()
    dest.mkdir(parents=True,exist_ok=False)
    manifest = json.loads((ROOT/'manifests/source-snapshot.json').read_text())
    restored = []
    for project in manifest['projects']:
        repo = dest/project['path']
        repo.mkdir(parents=True,exist_ok=False)
        if 'patch' in project:
            git(repo,'init','-q')
            git(repo,'config','core.autocrlf','false')
            upstream = str(args.upstream_cache.resolve()/project['path']) if args.upstream_cache else project['upstream_url']
            git(repo,'fetch','--quiet','--depth=1',upstream,project['upstream_base'])
            if git(repo,'rev-parse','FETCH_HEAD').decode().strip()!=project['upstream_base']:
                raise SystemExit('Unexpected source base: '+project['id'])
            git(repo,'checkout','--quiet','--detach','FETCH_HEAD')
            patch = (ROOT/project['patch']).read_bytes()
            if project['patch'].endswith('.gz'):
                patch = gzip.decompress(patch)
            git(repo,'apply','--index','--whitespace=nowarn','-',data=patch)
            if git(repo,'write-tree').decode().strip()!=project['tree']:
                raise SystemExit('Reconstructed tree mismatch: '+project['id'])
            state = 'exact prototype tree; original custom history not restored'
        else:
            prefix = project['snapshot']+'/'
            for name, entry in manifest['source_files'].items():
                if name.startswith(prefix):
                    target = repo/name[len(prefix):]
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes((ROOT/name).read_bytes())
                    target.chmod(int(entry['mode'],8)&0o777)
            state = 'reviewed snapshot; omissions listed in manifest' if project['omitted'] else 'exact tracked source snapshot'
        restored.append({'project':project['path'],'state':state})
        print(json.dumps(restored[-1]),flush=True)
    report = {'result':'PASS','projects':restored,'physical_phone_build_complete':False,
              'reason':'External owner-provided stock inputs, compiler setup and local signing keys are required; this command only restores source'}
    (dest/'restore-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)

if __name__ == '__main__':
    main()
