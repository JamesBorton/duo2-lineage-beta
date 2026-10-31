# Experimental release qualification

Target: beta 1 build 1793400160, integrating the measured widget-size correction.
This is community testing, not a daily-use qualification. No exact-release phone
or Windows result is claimed. See the final release manifest for actual build,
current-image gates, signatures and owner-input reconstruction hashes.

Earlier beta 1793371964 passed a full generic fresh install, usable setup/default with an absent setting
workspace, RIGHT PIN, core physical checks, boot success/checkpoint and stability
on one Duo 2, plus signed RAM-only classic fallback and normal restore. The clock
was clipped on that phone; the source correction then passed 35 targeted emulator
checks. Historical evidence is not relabeled as a phone test of this exact build.

Source patches reconstruct their recorded trees. The source companions retain
kernel/dependency pins, licenses and explicit legacy correspondence limits.
Stock partition operation data is withheld from the distributable kit. Keys,
firmware/full OTA, owner recovery and device captures are not public assets.

Remaining community qualification: this kit on real Windows, a genuinely locked
stock device's unlock path, exact-release hardware and sustained battery/thermal
behavior. No relock test is authorized or needed. CI/source checks do not establish
hardware acceptance, an exact clean-host binary rebuild or a legal certification.

The checked source branch and release assets are prepared locally first. A public
prerelease must remain labeled experimental; the untested paths above are not
converted into passes by publishing it. See [download verification](VERIFY-DOWNLOAD.md)
and [workspace fallback](WORKSPACE-FALLBACK.md).
