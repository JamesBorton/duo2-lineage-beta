# Installation status

There is no downloadable beta ROM or recovery in this repository yet.
Do not flash source archives or use an unrelated Duo 1/GSI installation guide for
this product. The public source snapshot intentionally lacks four HAL contracts.

When the first beta is published, its release page will provide a matching ROM,
recovery, SHA-256 checksums, exact prerequisites, first-install/update steps and
tested stock-restore instructions. Back up your data before unlocking or formatting.
Unlocking the bootloader erases data; first installation may also require a wipe.
Keep an official Microsoft recovery package for your own device available.

The prototype uses virtual A/B with vendor/ODM inside the dynamic partition group.
Slot and pending-snapshot checks matter. Do not manually switch slots or relock
the bootloader using assumptions from another device. Source verification tools
in this repository do not run ADB, fastboot, wipes or installation commands.

The dual-screen workspace is opt-in in the prototype and is cleared by a factory
reset. Public release instructions must explicitly cover enabling it and the
required reboot; successful firmware installation alone does not enable it.
