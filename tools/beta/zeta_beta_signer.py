#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""AOSP signing hook: retain the four owner-supplied images during regeneration.

Executed inside the AOSP sign_target_files_apks Python package. The hook adds
only input images that the standard signer otherwise drops. All normal signing,
image regeneration, AVB construction and error checking remain AOSP code.
"""
import os
from pathlib import Path
import shutil
import sys
import zipfile


def main():
    import add_img_to_target_files
    import sign_target_files_apks
    source = Path(os.environ['ZETA_BETA_SIGNING_INPUT'])
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
