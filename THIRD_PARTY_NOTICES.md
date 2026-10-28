# Third-party notices and provenance

| Component | Pinned source / attribution | Applicable terms |
|---|---|---|
| Android framework | [LineageOS/android_frameworks_base](https://github.com/LineageOS/android_frameworks_base), base 958afcc3d647d57571650cee4172afe0da619171; AOSP and LineageOS contributors | Existing file notices, predominantly Apache-2.0 |
| Launcher | [LineageOS/android_packages_apps_Launcher3](https://github.com/LineageOS/android_packages_apps_Launcher3), base f83fbe24ed3c0bd3c4d7cd3186ffadefeda5b7db | Existing file notices, predominantly Apache-2.0 |
| Kernel | [Microsoft final Duo 2 kernel](https://github.com/microsoft/surface-duo-oss-kernel.msm-5..4), base 177c60bdde799ce804bdcd1b87c51af5e80fde55 | Kernel COPYING, Linux-syscall-note and file-specific SPDX/notices |
| Imported techpacks and DTs | Exact repositories/revisions in manifests/kernel-inputs.json; original notices preserved inside the kernel patch | GPL/BSD/other file-specific terms; not relicensed Apache |
| Boot controller | [LineageOS/android_hardware_qcom_bootctrl](https://github.com/LineageOS/android_hardware_qcom_bootctrl/tree/846dfb0652cc142e1783cbe085783527bbe4a190); detailed imported-file map in bootctrl/upstream.json | AOSP Apache-2.0; Linux Foundation 2016 BSD-3-Clause; Qualcomm Innovation Center 2023 BSD-3-Clause-Clear |
| VNDK 30 and other Android inputs | Pinned upstream.xml, VNDK revision 5f9884aa352825291757dfd6694b874ad8c1805e | Obtain from upstream under their applicable component terms; no prebuilt binaries copied here |

BootControl.cpp, BootControl.h and main.cpp retain the Qualcomm 2023
BSD-3-Clause-Clear header. Its full text, including the absence of a patent
license, is in LICENSES/BSD-3-Clause-Clear.txt. The original Linux Foundation
BSD notice remains in bootctrl/NOTICE. Source publication includes these notices;
the prototype ROM's Soong notice metadata still needs reconciliation before a
new public binary release.

The kernel patch retains all imported headers and notices. Files marked as
modified are identified by the patch against the pinned public base; modifications
were made by this project in 2026. Copyright belongs to each respective holder.

Excluded dependencies: Microsoft/Qualcomm/other stock firmware is not licensed
by us and is not present. Four Archfx/duoVendor contracts from revision
60a3e8f6caacda6a9bafdc7c59d202f66fd8c9c8 are omitted while provenance/licensing
is resolved. Their history identifies contributions by Thai Nguyen (thai-ng),
Aruna Jayasena (Archfx) and Ethan Goh (Ethanol10); this is attribution information,
not a claim that any one person can grant all underlying rights.
