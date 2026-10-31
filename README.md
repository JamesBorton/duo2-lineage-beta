# Independent workspace beta for Surface Duo 2

Unofficial LineageOS 23.2 / Android 16 for **Surface Duo 2 only**. Independent
community project, not affiliated with Microsoft, Qualcomm or LineageOS.

## Experimental beta 1

This release is for community testing and feedback. The independent left/right
workspace activates automatically at Home after full-display setup. The clock
widget sizing correction is included. Read the scope below before installing.

**Download the complete installer kit from [Releases](https://github.com/JamesBorton/duo2-lineage-beta/releases).**
Extract it, open START-HERE.html and keep all files together. The source checkout
is for review/development; do not run an unstamped installer from a Git clone.

You need a Surface Duo 2, your own official Microsoft 2023.501.541 recovery ZIP,
Windows or Linux, Python 3.11+, Platform-Tools and 20 GB free. First installation
unlocks/formats and **erases data**. A supported beta update intends to retain data.
The helper verifies signatures, stock bytes, slots/snapshots, battery and actual
installed images. It never asks you to select a slot or enter a PIN on the computer.

The download is an **owner-input assembly kit**, not a full stock-containing ROM.
Your official ZIP stays on your computer and supplies the withheld stock data.
Your ADB private key and personalized recovery stay private. See [download design](docs/DOWNLOAD_KIT.md).
The kit contains a [security-review-first AI assistant prompt](tools/beta/AI-ASSISTANT-PROMPT.txt)
for help from an assistant that can inspect local files. AI review is optional and
is not an authenticity or safety guarantee.

## What is tested, and what remains open

Core fresh installation, setup/default workspace, PIN, displays/touch, RIGHT typing,
fold/reopen and signed fallback/normal restore passed on one phone with the earlier
beta 1793371964. The clock correction passed 35 targeted emulator checks. This exact
packaged build has its own automated image/emulator/signature reports and has not
been installed on the maintainer phone. No fresh physical claim is inferred.

**Real Windows installation, physical locked-bootloader unlock and unlisted everyday
hardware remain unqualified.** Calls/data/audio/Bluetooth/fingerprint/camera and
battery behavior need reports on this exact release. Classic fallback is retained.
Stock return is a separately reviewed manual process, not a one-click helper.
Do not relock the bootloader while using this beta.

Start with [testing scope](docs/TESTING.md), [known issues](docs/KNOWN-ISSUES.md),
[stock-return limitations](docs/RESTORE-STOCK.md) and [release readiness](docs/RELEASE_READINESS.md).
Report reproducible problems using the issue forms. Do not upload identifiers,
private keys, account details, stock firmware, personalized recovery or raw sessions.

## Integrity, sources and licensing

[Verify the kit](docs/VERIFY-DOWNLOAD.md) against the release SHA256SUMS and detached signature. The existing
beta certificate SHA256 fingerprint is:

`2192dea4f2e70b54b21cd99e8a37083c85aac2a1d7b7ae8066418bbcfdd0bc45`

This repository contains source patches, device/vendor integration recipes and
installer source, with exact upstream pins and retained licenses. It contains no
private project history, firmware binaries, built APKs or device captures.
Run `python tools/verify-public-tree.py` for source integrity/privacy checks.
See [source reproduction and correspondence limits](docs/SOURCES.md),
[licensing](LICENSING.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
Complete source companions and checksums accompany the release assets.
