#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""AOSP signing hook: retain owner images and protect read-only public certs.

Executed inside the AOSP sign_target_files_apks Python package. The hook adds
input images that the standard signer otherwise drops. Public certificates are
copied temporarily because AOSP ZipWrite chmods/utimes its inputs. All signing,
image regeneration, AVB construction and error checking remain AOSP code.
"""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile


def write_with_public_certificate_copy(writer, key_root, archive, filename,
                                     arcname=None, perms=0o644, compress_type=None):
    path = Path(filename)
    if path.resolve().is_relative_to(key_root.resolve()) and path.name.endswith('.x509.pem'):
        certificate = path.read_bytes()
        assert certificate.startswith(b'-----BEGIN CERTIFICATE-----')
        assert certificate.rstrip().endswith(b'-----END CERTIFICATE-----')
        with tempfile.TemporaryDirectory(prefix='zeta-public-certificate-') as directory:
            staged = Path(directory) / path.name
            staged.write_bytes(certificate)
            # Preserve AOSP's original archive name, bytes, mode and ZIP epoch.
            return writer(archive, str(staged),
                          arcname=str(filename) if arcname is None else arcname,
                          perms=perms, compress_type=compress_type)
    return writer(archive, filename, arcname=arcname, perms=perms,
                  compress_type=compress_type)


def main():
    import add_img_to_target_files
    import common
    import sign_target_files_apks
    source = Path(os.environ['ZETA_BETA_SIGNING_INPUT'])
    key_root = Path(os.environ['ZETA_BETA_KEY_ROOT'])
    zip_write = common.ZipWrite
    def protected_zip_write(archive, filename, arcname=None, perms=0o644, compress_type=None):
        return write_with_public_certificate_copy(zip_write, key_root, archive, filename,
                                                 arcname, perms, compress_type)
    common.ZipWrite = protected_zip_write
    original = add_img_to_target_files.main

    def preserve_owner_images(args):
        with zipfile.ZipFile(source) as incoming, zipfile.ZipFile(args[-1], 'a', allowZip64=True) as outgoing:
            for part in ('vendor', 'odm', 'vendor_boot', 'dtbo'):
                name = 'IMAGES/' + part + '.img'
                # AOSP regenerates dtbo from PREBUILT_IMAGES. Its firmware
                # prefix must remain identical; the independent release audit
                # verifies this plus the AVB metadata boundary.
                if name in outgoing.namelist():
                    assert part == 'dtbo', 'Unexpected pre-existing owner image: ' + part
                    continue
                with incoming.open(name) as src, outgoing.open(name, 'w') as dst:
                    shutil.copyfileobj(src, dst, 4 * 1024 * 1024)
        return original(args)

    add_img_to_target_files.main = preserve_owner_images
    sign_target_files_apks.main(sys.argv[1:])


if __name__ == '__main__':
    main()
