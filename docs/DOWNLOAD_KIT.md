# Owner-input beta download

The planned release is a portable assembly kit. It is not published yet.

You supply the official Surface Duo 2 recovery ZIP, obtained from Microsoft's
[Surface recovery page](https://support.microsoft.com/surface-recovery-image).
That page may require your serial number and Microsoft sign-in. The supported
input is ota_c1-12-customer_2023.501.541.zip, 3,228,333,341 bytes, SHA256:

```
8e695f5e7d4a88ee76d06d4457fd6f203f4c65f35aa0c3e0a87961e24ec5c302
```

The kit contributes the newly built Android images and an assembly recipe. It
excludes every operation-data range for vendor, odm, vendor_boot and dtbo. It
copies matching compressed bytes from your stock ZIP or re-encodes your stock
image chunks with BZ2/raw operations. Any stock firmware-prefix difference is an
error; only explicitly bounded AVB metadata edits may be supplied. There is no
fallback that downloads or embeds a missing stock chunk.

Python 3.11+ on Windows or Linux reconstructs the complete signed OTA locally.
The assembler verifies the input, kit, chunk and final-file hashes. ZIP signature
bytes are retained, so the result must be byte-identical to the tested installer.
No ADB, phone operation or network access occurs during assembly. It refuses an
existing output. Allow generous temporary disk space; exact needs will accompany
the tested release. Do not sideload a partial result or a mismatched ZIP.

The eventual command will be:

```sh
python3 assembly.py assemble --kit /path/to/beta-kit --stock /path/to/ota_c1-12-customer_2023.501.541.zip --output /path/to/lineage-zeta-beta.zip
```

This design keeps stock binaries out of the public download. It grants no rights
to them and does not certify the assembled result for uses beyond its applicable
component terms. Follow only the exact release's tested install instructions.
