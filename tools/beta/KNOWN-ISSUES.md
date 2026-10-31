# Scope and known limitations

- **Experimental Surface Duo 2 build.** Tested core behavior on one phone is not a
  guarantee for every device, host computer or hardware feature.
- **Windows and locked unlock remain unqualified.** The portable helper has offline
  tests, but this final kit has no real Windows run or physical locked-bootloader
  unlock test. The maintainer's fresh-install phone was already unlocked.
- **Bootloader USB transport can be unreliable.** Identity queries returned blank/
  unsupported replies and a RAM upload timed out in retained tests. USB reconnect
  and a full ordinary restart resolved particular attempts; the cause is unproven.
  The helper stops rather than skipping checks. Keep the current screen and session.
- **Recovery cannot always read battery level.** A normal-Android reading expires
  after 15 minutes. If it expires before sending, a checked return to normal Android
  and a fresh session is needed. After a completed format, that can require setup
  again. USB power does not substitute for measured battery evidence.
- **Host progress near 47% can be normal.** Watch recovery, choose No for additional
  apps, then leave it open for verification. Never reboot during an active install.
- **Stock return is a separate manual procedure.** There is no one-click stock
  restore or relock button. Read RESTORE-STOCK.md before installing.
- **Hardware coverage is incomplete.** Cellular, audio, Bluetooth, fingerprint,
  cameras and sustained battery/thermal behavior need community reports for this
  exact release. Historical checks on other builds are not carried forward as passes.
- **Legacy kernel/vendor baseline.** The kernel is built from pinned Microsoft
  final-source inputs, retaining stock module compatibility. Modern framework
  security patch dates do not establish that all old kernel/vendor issues are fixed.
- **Custom workspace limits.** Launcher3 is required for independent Home. Microsoft
  proprietary shell/peek/pen-service parity is not promised. Google apps are not
  provided by this kit. Unsupported Home selection falls back to classic policy.
- **Clock correction scope.** The measured-size fix is integrated in this candidate
  and has emulator evidence. It has not been applied to the maintainer phone as an
  app update or physically qualified in this exact release.

Keep the bootloader unlocked while using the beta. Do not relock, manually select
slots, accept an authentication/signature bypass or choose recovery's Enable ADB.
