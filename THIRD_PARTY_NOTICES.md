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
the beta source's Soong metadata includes all three applicable texts. Runtime
notice delivery is checked separately for the exact signed build.

The kernel patch retains all imported headers and notices. Files marked as
modified are identified by the patch against the pinned public base; modifications
were made by this project in 2026. Copyright belongs to each respective holder.

Retired dependencies: the four copied Archfx/duoVendor contracts are absent
from the beta source and build. The replacement adapter's provenance and prior
exposure are documented in posture/controller/README.transport.md. Old history
is private and is not relicensed or published here.

Microsoft/Qualcomm stock binaries are absent. The planned assembly kit requires
each owner to obtain the official package and contributes none of its four stock
partitions' payload bytes. Root Apache terms do not license those inputs.

WebView 156.0.8078.47 contains 769 credited components and 2,102 copyright mentions.
It has mixed component terms, not a blanket Unicode license. Source provenance:

- Chromium: [1d17a2e2ee147bb7d6ae2ab6abdb3a2510c17775](https://github.com/chromium/chromium/tree/1d17a2e2ee147bb7d6ae2ab6abdb3a2510c17775).
- FFmpeg: [9db86ce5b5b454dfc96c435f9f0723012980c37f](https://chromium.googlesource.com/chromium/third_party/ffmpeg/+/9db86ce5b5b454dfc96c435f9f0723012980c37f).
- Lineage patches: [ef69054c74f7d8306446969136c806738169f1e1](https://github.com/LineageOS/android_external_chromium-webview_patches/tree/ef69054c74f7d8306446969136c806738169f1e1).
- Prebuilt revision: 5de662a4d42b57a2efe4114e499d38fa3ce41f9d;
  ARM64 APK SHA256 1d2f61832b2596b0046cb82cf3634609ea866098d097a83fac27c35272ac726a.

Embedded credits HTML SHA256:
bb9a402c6f072f7728bd97c67b25bcd2b1f962fb72b4148dc6241781c0fc277c.
The credits include FFmpeg/LGPL and component-specific notices. Runtime WebView
credits access passed on the emulator; ARM64 phone access remains to be checked.
Upstream enables proprietary_codecs and ffmpeg_branding=Chrome. No additional
codec patent rights or clearance are claimed. Google's Sans Flex font has an OFL
grant; it is not an unlicensed Google font merely because it is from Google.

The owner recovery preparation tool includes an unmodified AOSP avbtool.py at
revision91f1bfc948d35265c3b1e5e97bf1c410e65d18fa. Its original MIT permission,
copyright and warranty text remain at the start of that file. See
tools/beta/third_party/provenance.json for its source and digest.
