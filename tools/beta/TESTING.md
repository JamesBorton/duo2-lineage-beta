# Experimental beta testing

This release invites community feedback. It is not a daily-use qualification or an
official Microsoft/LineageOS release. Surface Duo 2 only; the original Duo is unsupported.

## What has actually been checked

The earlier beta 1793371964 passed a complete stock-to-beta fresh installation on
one maintainer Duo 2, usable setup, automatic independent workspace at first Home
with no opt-in, both displays/touch, independent apps, RIGHT keyboard/PIN unlock,
closing/reopening, signed classic fallback and normal workspace restoration.

The clock sizing correction passed 35 targeted emulator checks, including an old
APK negative control, existing layout preservation, fresh widgets, both panels,
rotations, larger text, folded layouts and classic fallback/restart. The release
candidate also has its own current-image emulator and signed-package reports in
the accompanying release manifest. These are distinct from phone acceptance.

This exact packaged release has not been installed on the maintainer phone.
Real Windows installation and locked-bootloader unlocking have not been physically
qualified. Older Windows reconstruction tests do not certify this kit.

## Useful feedback

Please first report your computer OS, Python/Platform-Tools versions, release build,
prior ROM, and whether the bootloader was already unlocked. Follow START-HERE;
never skip a failed signature, hash, slot, snapshot or battery check.

After a successful install, check:

- Setup controls and first Home; independent workspace should appear automatically.
- Both screens/touch, different apps on each side, keyboard placement and private PIN unlock.
- Clock time/date, rotation, larger text, widget resizing and reopening the phone.
- Wi-Fi, ordinary calls/SMS/mobile data, Bluetooth, audio/microphone, cameras and fingerprint.
- Charging, sleep/wake and overnight battery usage. Include the conditions and duration.

Use the repository's issue forms. Describe steps, expected result and actual result.
Do not upload your whole working folder, stock ZIP, personalized recovery, adbkey,
PIN, account details, device identifiers or unredacted logs/screenshots. The maintainer
can request a specific redacted excerpt. No automatic telemetry or log upload is required.

If a check stops, leave the screen unchanged and retain the local session. Do not
repeat a sender, select slots, disable security or use a wipe as a repair shortcut.
