#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare private signed beta target-files. Never accesses a phone or publishes.

Private inputs and outputs contain owner-supplied firmware; do not upload them.
The later stock-input assembly kit is the only planned OTA download artifact.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import shlex
import zipfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree', type=Path, required=True)
    ap.add_argument('--target-files', type=Path, required=True)
    ap.add_argument('--keys', type=Path, required=True)
    ap.add_argument('--stock-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--prepared-input', type=Path, help='Reuse an independently checked prepared signing ZIP')
    ap.add_argument('--prepared-notices', type=Path, help='Matching prepared notice target-files ZIP')
    args = ap.parse_args()
    assert not args.output.exists(), 'Use a new private output directory'
    args.output.mkdir(parents=True)
    scripts = Path(__file__).resolve().parent
    host = args.tree / 'out-zeta/host/linux-x86'
    keys = json.loads((args.keys/'key-inventory.json').read_text())
    env = os.environ.copy()
    env['PATH'] = str(host/'bin') + ':' + env['PATH']
    stripped = []
    old_release = 'build/make/target/product/security/testkey'
    assert old_release in keys['apk_key_mapping']
    assert bool(args.prepared_input)==bool(args.prepared_notices)
    if args.prepared_input:
        signing_input=args.prepared_input
        notices=args.prepared_notices
        assert signing_input.is_file() and notices.is_file()
        with zipfile.ZipFile(signing_input) as src,zipfile.ZipFile(notices) as original:
            assert src.read('META/zeta_notice_corrections.json')==original.read('META/zeta_notice_corrections.json')
            assert src.read('META/otakeys.txt').decode().strip()==old_release+'.x509.pem'
            assert 'extra_recovery_keys=\n' in src.read('META/misc_info.txt').decode()
            for name in src.namelist():
                if name.endswith('/adb_keys'):
                    assert not src.read(name).strip()
                    assert (src.getinfo(name).external_attr>>16)&0o170000==0o100000,'Prepared adb_keys must be a regular empty file'
                    stripped.append(name)
    else:
        subprocess.run(['python3', str(scripts/'prepare-beta-notices.py'), '--target-files', str(args.target_files),
                        '--output-dir', str(args.output/'notices'), '--host-tools', str(host/'bin'),
                        '--stock-root', str(args.stock_root), '--webview-source', str(args.tree/'external/chromium-webview/prebuilt/arm64/webview.apk')], check=True, env=env)
        notices = args.output/'notices/target-files-notices.zip'
        signing_input = args.output/'target-files-signing-input.zip'
        with zipfile.ZipFile(notices) as src, zipfile.ZipFile(signing_input, 'w', allowZip64=True) as dst:
            for info in src.infolist():
                if info.filename.endswith('/adb_keys'):
                    stripped.append(info.filename)
                    clean=copy.copy(info)
                    # adb_keys can be a symlink in target-files. An empty
                    # symlink target cannot be extracted; publish an empty
                    # regular key file instead and preserve secure ADB.
                    clean.external_attr=(0o100644<<16)
                    dst.writestr(clean, b'')
                elif info.filename == 'META/misc_info.txt':
                    lines = src.read(info).decode().splitlines()
                    lines = ['extra_recovery_keys=' if x.startswith('extra_recovery_keys=') else x for x in lines]
                    assert 'extra_recovery_keys=' in lines
                    dst.writestr(copy.copy(info), '\n'.join(lines)+'\n')
                elif info.filename == 'META/otakeys.txt':
                    dst.writestr(copy.copy(info), old_release+'.x509.pem\n')
                else:
                    with src.open(info) as source, dst.open(copy.copy(info), 'w') as destination:
                        shutil.copyfileobj(source, destination, 4*1024*1024)
    assert {'BOOT/RAMDISK/adb_keys','ROOT/adb_keys'} <= set(stripped)
    # Use the release tool's own embedded Python and libraries. A source hook is
    # added to a private copy, preserving the executable prefix and original AOSP
    # modules. This avoids mixing the system Python ABI with packaged bytecode.
    native = host/'bin/sign_target_files_apks'
    tool = args.output/'sign_target_files_apks-owner-images'
    shutil.copy2(native, tool)
    with zipfile.ZipFile(tool) as archive:
        entry = archive.read('__main__.py').decode()
    needle = 'runpy._run_module_as_main("sign_target_files_apks", alter_argv=False)'
    assert entry.count(needle) == 1
    # A zip append intentionally supersedes only this launcher entry. Source
    # and original tool hashes are recorded; this tool is not a release asset.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(tool, 'a') as archive:
            archive.writestr('__main__.py', entry.replace(needle, 'import zeta_beta_signer; zeta_beta_signer.main()'))
            archive.writestr('zeta_beta_signer.py', (scripts/'zeta_beta_signer.py').read_bytes())
    tool.chmod(0o700)
    env['ZETA_BETA_SIGNING_INPUT'] = str(signing_input)
    output = args.output/'target-files-beta-signed.zip'
    command = [str(tool), '-v', '-p', str(host), '-o']
    for old, new in sorted(keys['apk_key_mapping'].items()):
        command += ['-k', old+'='+new]
    for name, key in sorted(keys['apex_payload_keys'].items()):
        command += ['--extra_apex_payload_key', name+'='+key['private_key']]
    # This AOSP version passes the APK-name map to GetApexKeys. Explicit APEX
    # container mappings are therefore necessary even with complete -k rules.
    with zipfile.ZipFile(signing_input) as src:
        rows=[dict(p.split('=',1) for p in shlex.split(line)) for line in src.read('META/apexkeys.txt').decode().splitlines() if line.strip()]
        for row in rows:
            if row['container_certificate']=='PRESIGNED':continue
            old=row['container_certificate'].removesuffix('.x509.pem')
            command += ['--extra_apks',row['name']+'='+keys['apk_key_mapping'][old]]
    # Upstream prebuilt WebView has its own existing signer. Preserve its exact
    # bytes and signature, rather than applying its generic apkcerts placeholder.
    command += ['--extra_apks','webview.apk=']
    for part in ('vbmeta', 'vbmeta_system'):
        command += ['--avb_'+part+'_key', str(args.keys/'avb-root.pem'),
                    '--avb_'+part+'_algorithm', 'SHA256_RSA4096']
    command += [str(signing_input), str(output)]
    with (args.output/'signing.log').open('w') as log:
        subprocess.run(command, cwd=args.tree, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = {'state':'signed_target_files_created_not_yet_release_verified', 'source_target_files_sha256':sha(args.target_files),
              'notice_input_sha256':sha(notices), 'signing_input_sha256':sha(signing_input),
              'signed_target_files_sha256':sha(output), 'aosp_signer_sha256':sha(native),
              'owner_image_hook_sha256':sha(scripts/'zeta_beta_signer.py'),
              'maintainer_adb_key_entries_cleared':stripped, 'extra_upstream_recovery_trust_removed':True,
              'apk_roles':len(keys['roles']), 'apex_payload_roles':len(keys['apex_payload_keys']),
              'presigned_apex_exceptions':keys['presigned_apex_exceptions'], 'physical_device_used':False,
              'public_binary_release_ready':False}
    (args.output/'signing-preparation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
