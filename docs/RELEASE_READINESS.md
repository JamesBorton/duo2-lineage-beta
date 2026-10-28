# Public beta readiness

2026-10-28: candidate **1793224122** is signed and staged privately. No
downloadable ROM beta is published. This records engineering evidence and its
limits; it is not a legal opinion or permission from third-party rights holders.

Completed:

- Six public source projects reconstruct against their recorded bases. Fresh
  public history, source hashes and scoped licenses retain applicable upstream
  terms. No private source history or signing keys are published.
- Four copied HAL contracts and generated vendor classes were replaced by an
  original narrow AOSP HwBinder adapter. All 25 current-image emulator gates and
  11 transport/controller instrumentation tests pass. Prior exposure is disclosed;
  no clean-room certification is claimed.
- The final signed target-files pass independent checks of 123 APKs, 37 APEXes,
  embedded APKs, MAC signer policy, AVB, VINTF, SELinux, care maps and notice XML.
  Dedicated protected beta keys sign the new build. The upstream CTS shim is an
  explicit preserved exception; WebView retains exact upstream bytes/signature.
- OTA whole-file and payload signatures pass. No maintainer ADB key remains in
  normal boot/recovery. Its OTA trust contains only the beta certificate.
- Real Windows and Linux owner-input reconstructions produce identical signed
  OTA bytes: 1,952,419,447 bytes. Independent interval checks prove all four stock
  partitions' operation data is excluded from the public kit; 920,649,677 payload
  bytes are supplied from the owner's official ZIP.
- Owner recovery preparation is byte-identical on Windows/Linux. Two temporary
  physical boots pass with authenticated owner-only root ADB, Enforcing SELinux,
  QTI/UFS and snapshot checks. Do not select the menu action that disables auth.
- Portable host tests pass on both systems: eight assembly, five recovery framing/
  trust and seven slot-preflight guard tests. Physical installation remains separate.
- Readable supplemental notices include all 769 WebView component sections and
  the full credits. Kernel source, conservative userspace source candidates,
  exact FFmpeg source and historical API30 libnl/libexif source histories are staged.

Remaining gates before publishing download assets:

- Finish the authorized clean beta installation, verify recovery status 0, all
  ten installed partition hashes, direct boot hash and target QTI/UFS state; then
  verify normal Android build, boot success, snapshot completion and stability.
  At this checkpoint sideload is still active; installation success is unconfirmed.
- Complete fresh setup and exact-build physical acceptance: panels/touch, both
  folded sides, close/wake, independent apps, shared Recents, toss/buttons,
  keyboard/unlock placement, Wi-Fi, cameras and charging. Identify untested
  features clearly rather than claiming full hardware support.
- Test the beta-to-beta data-preserving update and official-stock restore paths,
  then publish their tested commands and wipe implications. Old prototype restore
  success is not evidence for this new signing transition.
- Review remaining source correspondence limits. The historical Google VNDK
  build manifests are unavailable; complete API30 source histories and the
  published binary-import provenance are supplied. Branch correspondence is an
  explicit inference; an exact legacy binary rebuild is not claimed.
- Refresh and seal the final kit, publish matching source/notices/certificates and
  signed checksums, and confirm CI on the exact public source commit. No clean-host
  bit-identical full-ROM rebuild is currently claimed.

The owner-input kit does not distribute stock vendor/ODM images, Microsoft
modules, vendor_boot or DTBO operation data. This limits the project's download;
it grants no rights in stock firmware. Directly distributing those stock binaries
would reopen the unresolved stock source/permission questions. See
[source evidence](SOURCES.md), [signed candidate](../manifests/signed-candidate-validation.json)
and [reconstruction](../manifests/owner-input-reconstruction.json).
