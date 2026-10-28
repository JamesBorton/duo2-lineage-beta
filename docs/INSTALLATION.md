# Installation status

No downloadable beta is published yet. Candidate 1793224122 has passed offline
ROM/signature checks and real owner-input reconstruction on Windows/Linux.
Authenticated temporary recovery and read-only slot checks pass on the phone;
clean ROM installation and physical acceptance are in progress. The old HAL contracts have been replaced and are no longer required.

The planned download is an owner-input kit plus the exact normal boot image,
public certificates, recovery recipe, sources, notices and checksums. Each owner
obtains official recovery2023.501.541 from Microsoft and reconstructs the tested
signed OTA. Do not flash source archives or substitute a Duo1/GSI guide.

The prototype-to-beta signing transition requires a clean install that erases
apps, settings and personal data. A previous prototype backup decision is not a
current backup decision. Exact release instructions and phone acceptance must be
completed before this preparation is treated as an installation guide.

The intended supervised flow is: verify all downloads and the official stock
input; assemble the OTA; prepare an owner-authorized temporary recovery; inspect
the phone's bootloader/slots; temporarily boot that recovery; let the embedded owner key authenticate ADB and run
the recovery preflight; format only after an explicit backup/wipe decision;
refresh preflight immediately before sideload; sideload and check status0 plus
target partition hashes and QTI/UFS state; boot Android; finish setup and verify
successful boot and snapshot completion. Later updates need fresh checks too.
Never assume A or B is the active/healthy slot from an earlier session.

The new preflight tool accepts an explicit owner USB serial and checks current
versus active slot, source health, kernel suffix, UFS boot LUN, merge status and
snapshot records. It mounts metadata only ro,noload and unmounts it. Its seven host guard
tests pass on Windows/Linux, and it has passed on the exact physical beta recovery
before and after the authorized clean reset. Normal ROM acceptance remains pending.
It does not install, wipe, choose a slot, or authorize any of those operations.
Keep its reports private because they identify the phone.

This device has boot/vendor_boot/DTBO and virtual A/B super partitions. There is
no separate recovery, init_boot or vendor_dlkm partition. Temporary recovery is
for fastboot boot on an unlocked device. Never flash it into the ROM or relock
the bootloader. Preserve your official stock package for rollback; rollback
instructions must be tested with the exact release and include their wipe risk.

Workspace defaults OFF and a factory reset clears the setting. After Android
setup, authorize your own PC normally through USB debugging. The tested opt-in
setting is `adb shell settings put global zeta_workspace_enabled 1`, followed by
a normal reboot. The eventual release guide will include this step explicitly.

Do not select Advanced -> Enable ADB in an owner-authorized recovery. In this
Lineage version that menu action disables recovery authentication. The matching
owner-key image connects automatically on the unlocked device and preserves
authentication. Preflight rejects an explicitly disabled recovery-auth property.
A missing snapshot-state file after a clean metadata format is accepted only
alongside no snapshot records and QTI merge status NONE.

The current sideload was started without automatic reboot so installed bytes can
be checked first. Recovery may ask whether to reboot recovery to install more
packages before the PC's sideload command returns. With no add-ons, choose No;
then require the latest installation status 0. ADB's percentage is not the
installation result. Do not bypass a signature failure or repeat an erase to
escape this prompt. Exact public steps will follow the completed acceptance run.


Temporary recovery must remain running when entering sideload. Select
**Apply update -> Apply from ADB in its menu**. Do not use `adb reboot sideload`:
on this build that command performs a real reboot, discarding RAM-booted
recovery and returning to the installed slot's recovery and OTA trust. During the
prototype-to-beta transition that older recovery rejects the new signature.
The first maintainer attempt exposed this sequence fault; the warning was
declined. ADB exit 0 is only a transport result. Check the actual recovery status
and matching recovery identity before treating an installation as successful.
