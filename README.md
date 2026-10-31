# A Surface Duo 2 Lineage OS ROM with Stock-like screen behavior

I'm James. SWE by trade. Not a phone dev.

This project has been "vibe coded" using 6.1 Sol and 6 Astra. I wanted to see what
I could get working on my Surface Duo 2, and this is where we ended up.

## What is this?

It's an experimental custom ROM for the Surface Duo 2, built on unofficial
LineageOS 23.2 / Android 16. Installing it replaces Microsoft's stock Android
software on the phone with this build.

The idea is to get a newer version of Android running while keeping the dual-screen
stuff that makes a Duo a Duo. It includes a custom workspace with independent
left and right Home screens, so you can use a different app on each side.

Some of the stock-like Duo features are built in and working on mine:

- Two separate screens, with a different app on each
- Fold it back to use one screen at a time
- Double-tap the screen you want to use to switch sides when folded back
- Toss apps between screens
- Move an app to the other screen through Recents
- Different orientations, including portrait and landscape

**This process is not for the faint of heart.** I can't guarantee it'll work for
your phone. The beta has worked for mine, though. This is not a daily driver for
me, and I'm putting it out here so other people can try it and tell me what works,
what doesn't, and what I've missed.

## What actually works?
This is not my daily driver, I have not tested all things extensively.

I've personally tested:

- Fingerprint scanner
- Bluetooth
- Both touch screens
- Wi-Fi
- Front and back cameras
- Flashlight
- Audio

Those are my observations on my phone, not a promise about yours or an exhaustive
test of every feature. Calls, mobile data and long-term battery behavior still
need proper testing. If you try something, please report back.

Setup, the independent workspace, typing and PIN unlock on the right screen, closing/reopening
and the classic-layout fallback have also been checked on an earlier beta.
The latest packaged build includes a clock-widget fix tested in the emulator;
I haven't reinstalled that exact build on my phone. The detailed
[testing notes](docs/TESTING.md) keep the phone checks and automated checks separate.

## What about the original Surface Duo?

No idea whether this could be made to work on the original Duo. I only have a
Duo 2. **This release and its installer target the Duo 2; the installer won't accept
an original Duo.** Please don't try to force it past that check.

## Want to give it a go?

**[Download the installer kit from Releases](https://github.com/JamesBorton/duo2-lineage-beta/releases).**
Extract the whole ZIP, open **START-HERE.html**, and keep the files together.
GitHub's source-code ZIP is not the installer.

I recommend using the included
[agentic AI prompt](tools/beta/AI-ASSISTANT-PROMPT.txt). Give it to Claude, Codex or
an agentic AI of your choice that can inspect the extracted files. It starts with
a security sweep of the installer code, then helps you through the process.
An AI review isn't a guarantee of safety, either.

If you're feeling feisty, go for it with the guide yourself. Either way, read the
[known issues](docs/KNOWN-ISSUES.md) and [stock-return notes](docs/RESTORE-STOCK.md)
before you start.

You'll need:

- A Surface Duo 2 and a backup of anything you care about
- Your own official Microsoft **2023.501.541** recovery ZIP (you get this online, outlined in the installation process)
- Windows or Linux, Python 3.11+, Android Platform-Tools and 20 GB free
- Some patience, a charged phone and a USB cable that behaves itself

**First installation erases your apps, files and PIN.** A compatible beta update
is intended to keep your data, but back it up anyway. I haven't tried this kit on Windows or used it to
unlock a genuinely locked phone yet. So far works fantastic on Arch Linux. Don't relock the bootloader while using the beta.

The kit builds the signed installer locally using your Microsoft recovery ZIP.
I'm not distributing the stock firmware, and your private keys and personalized
recovery stay on your computer. More on that [here](docs/DOWNLOAD_KIT.md).
If a signature, hash, battery or device check fails, stop and ask for help rather
than bypassing it. Stock restore is a separate manual process, not a button in
this installer.

## Google apps and app stores

This does **not** come with Google apps. You can install apps or other app stores
yourself. Adding Google apps is up to you, too; I haven't tested or provided a
Google-apps installation procedure for this ROM.

## Tell me what you find

[Open an issue](https://github.com/JamesBorton/duo2-lineage-beta/issues) with the
build you're using, what you tried and what happened. For install problems, include
your computer OS and the step where it stopped. Please leave out PINs, device
identifiers, private keys, account details and full unredacted logs. Don't upload
your stock ZIP or your whole working folder.

## Checksums, source and the boring but necessary bits

[Verify your download](docs/VERIFY-DOWNLOAD.md). The beta signing certificate's
SHA256 fingerprint is:

`2192dea4f2e70b54b21cd99e8a37083c85aac2a1d7b7ae8066418bbcfdd0bc45`

Source patches, installer code, upstream pins and licenses are here for review.
See [sources](docs/SOURCES.md), [licensing](LICENSING.md),
[third-party notices](THIRD_PARTY_NOTICES.md) and
[release qualification](docs/RELEASE_READINESS.md). This is an independent project,
not affiliated with Microsoft, Qualcomm or LineageOS.
