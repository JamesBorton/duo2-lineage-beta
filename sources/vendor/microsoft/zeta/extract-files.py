#!/usr/bin/env python3
"""Stage local references to verified extracted stock files. No device access."""
import hashlib, json, os
from pathlib import Path
stock = Path(os.environ.get('DUO2_STOCK_ROOT', str(Path.home() / 'android/stock/2023.501.541'))).resolve()
root = Path(__file__).resolve().parent / 'proprietary'
assert (stock / 'stock-inventory.json').is_file(), 'Run inspect-stock.py and verify the payload first'
inventory = json.loads((stock / 'stock-inventory.json').read_text())
assert inventory['source_zip_sha256'] == '8e695f5e7d4a88ee76d06d4457fd6f203f4c65f35aa0c3e0a87961e24ec5c302'
for entry in inventory['partitions']:
    if entry['name'] in ('vendor','odm','dtbo','vendor_boot'):
        image = stock / 'images' / (entry['name'] + '.img')
        assert image.stat().st_size == entry['size']
        with image.open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == entry['sha256'], image
root.mkdir(exist_ok=True)
for name, src in [('images',stock/'images'), ('vendor',stock/'vendor-tree'), ('odm',stock/'odm-tree'), ('boot',stock/'unpacked/vendor_boot')]:
    assert src.is_dir(), src
    dst = root/name
    if dst.is_symlink(): assert dst.resolve() == src.resolve()
    else:
        assert not dst.exists(), dst
        dst.symlink_to(src, target_is_directory=True)
print('Stock references staged; proprietary content remains outside Git.')
