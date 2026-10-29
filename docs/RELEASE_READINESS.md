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

- The exact signed beta installs with actual RSA verification result 0, recovery
  status 0 and all ten installed hashes verified. Normal B boot matches the signed
  binaries, is Enforcing, and records boot success/checkpoint commit. Bootloader
  readback confirms B successful and bootable. Normal and enabled-workspace
  stability runs each exceed 122 seconds without core-process restarts/crashes.
- Owner checks on this beta pass both panels/touch, independent apps, RIGHT typing,
  folded switching, close/reopen, shared Recents, both buttons, bidirectional toss
  with task-state retention, Wi-Fi and front/rear Aperture previews. Closing/
  reopening after 30 seconds unplugged and the right-default PIN also pass. [Device evidence](../manifests/physical-beta-validation.json).

Remaining gates before publishing download assets:

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
