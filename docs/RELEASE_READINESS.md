# Public beta readiness

2026-10-28: no downloadable ROM beta is published yet. This document records
engineering evidence and remaining release gates; it is not a legal opinion.

Completed:

- Fresh public history, scoped Apache-2.0 contributions, retained upstream terms,
  source hashes and verified exact patch reconstruction.
- The four old HAL contracts and generated vendor classes have been replaced by
  a narrow original AOSP HwBinder adapter. Three new transport tests pass; prior
  exposure and compatibility facts are documented in its README. No formal
  clean-room claim is made.
- All 25 current-source emulator gates pass, including display power, rendered
  keyboard input, default unlock pane, Recents, preview geometry and screen actions.
- Boot controller license metadata now includes Apache, BSD and BSD-Clear texts.
- Dedicated APK/APEX/AVB beta keys were generated outside Git and have verified
  protected backups. Actual signed output verification remains a separate gate.
- ARM64 WebView's embedded credits, version and exact Chromium/FFmpeg/Lineage
  source pins are identified. The credits page works on the test emulator.
- The owner-input assembler passes eight positive/negative tests on Windows and
  Linux. These synthetic tests do not establish real-ROM reconstruction.

Still required before publishing downloadable beta assets:

- Finish the exact phone candidate, release signing and all package, AVB, OTA,
  VINTF, policy, notice and privacy checks. Verify shipped APK and APEX identities,
  OTA trust, and removal of maintainer-specific recovery authorization.
- Produce the owner-input kit and independently verify that all four stock
  partitions' payload bytes are excluded. Reconstruct the real signed installer
  on Windows and Linux and verify its full hash and signatures.
- Deliver exact corresponding source/build materials and readable notices for
  distributed open-source components. Stock module source/permission gaps remain
  relevant if anyone proposes directly distributing those binaries.
- Complete fresh-source reproduction checks; no bit-for-bit clean-host rebuild
  is currently claimed.
- Obtain approval for a clean transition from prototype development signing to
  beta signing. Repeat physical hardware, installation, recovery, update and
  restore acceptance on the exact release, with current slot/snapshot checks.
- Publish checksums, public certificates, minimum stock input, known issues,
  security limits and tested instructions alongside the allowlisted assets.

The intended kit obtains stock bytes from the owner's exact official recovery
ZIP. It does not deliver stock vendor/ODM images, Microsoft modules, vendor_boot
or DTBO bytes in the public download. This design limits what this project
distributes; it does not grant rights in stock firmware or settle every question
about third-party terms. Existing private prototypes are not public releases.
