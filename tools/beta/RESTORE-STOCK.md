# Returning to Microsoft stock

Stock return erases apps, files and credentials. Make a current backup/data-loss
decision before starting. This installer does not contain an automated restore
button. Read this limitation before deciding to test the beta.

A reviewed beta-to-stock-and-back procedure was successfully exercised on the
maintainer phone using the exact Microsoft2023.501.541 recovery ZIP. It does not
make an arbitrary recovery, direct stock sideload into beta recovery, or another
stock version safe. The private operator used for that validation is not a generic
public restore utility and must not be copied with someone else's serial/paths.

## The verified procedure's stages

1. Obtain the exact official Microsoft recovery ZIP and verify its identity and
   signatures. Retain the matching beta recovery and a tested return path locally.
2. Verify the actual running beta, device, battery, current/active healthy slot,
   UFS boot LUN, no snapshots/merge and original stock firmware bytes using matching
   authenticated recovery. A prior installation log is not a fresh preflight.
3. Under a concrete reviewed plan, stage the ZIP's **unmodified original OEM boot**
   only on the machine-detected current slot. Do not choose or switch slots. Do not
   boot an OEM kernel over beta system data as a troubleshooting experiment.
4. Enter original Microsoft recovery using the physical menu and verify the actual
   product/build text. Only after current erase consent, perform its factory reset
   and manually choose Apply update from ADB. Send the original verified Microsoft ZIP once.
5. Require the actual sender exit and recovery status0. Before ordinary stock boot,
   verify the automatic target, QTI/UFS state and all29 installed stock image hashes
   at their signed payload lengths. No manual slot change is part of this procedure.
6. Boot stock, complete setup and verify the actual stock identity. A later beta
   installation uses First installation from supported stock and erases again.

These are safety requirements, not a command list to improvise. Ask for a reviewed
procedure matched to your actual device state before step3. No current portable
stock-restore helper is qualified for this release. If that support/rollback limit
is unsuitable for you, defer installation.

Do not relock the bootloader from the beta or use another ROM's restore script.
Keep OEM packages, private keys, personalized recoveries and raw evidence private.
Microsoft's official downloads/instructions are linked from START-HERE; they do not
replace the additional beta-to-OEM transition checks above.
