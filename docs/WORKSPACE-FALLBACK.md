# If the independent workspace will not work

Stop and ask for help using the installation issue form. Keep your exact release
number and local session. Do not factory reset, change slots or relock as a repair.

The project retains a signed, build-matching **temporary classic-layout boot** for
support-assisted diagnosis. It forces the normal Android boot with workspace-safe
mode, keeping the installed boot partition and explicit workspace preference
unchanged. A later ordinary reboot returns to the installed normal layout. This
is not stock firmware, a stock-restore image or another installer.

The optional `Duo2-workspace-safe-1793400160.img` asset is for that reviewed support
procedure only. **Do not flash or sideload it.** It is not the normal-user download.
Do not use a different build's image or an improvised fastboot command.

Before a temporary boot, support must establish the actual current build, exact
installed boot hash, authenticated recovery identity, healthy current/active
slot, QTI/UFS consistency and absence of snapshots or an active sender. The full
fresh bootloader identity checks must pass; a blank/unsupported reply is a stop,
not permission to skip a check. The matching image's checksum and AVB signing key
must also verify. No manual slot selection or security bypass is needed.

You enter the PIN privately after the temporary boot and confirm that classic
Home works. Normal restoration requires one reviewed ordinary reboot and new
runtime, workspace/data, boot-success and stability checks. The maintainer's
1793371964 phone passed that sequence; the exact new image has offline signature
and emulator validation only. Do not treat its physical behavior as qualified.

The generic installer does not automatically run this recovery procedure. A
separate backup/data-loss decision and a different reviewed plan are required
for stock restore; see [RESTORE-STOCK.md](RESTORE-STOCK.md).
