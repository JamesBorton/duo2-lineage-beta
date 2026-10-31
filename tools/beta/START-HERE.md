# Surface Duo 2 beta — start here

**Experimental beta. Surface Duo 2 only.** Keep this folder together.
Community testing preview: read the known issues and supported scope before installing.

## Before you start

- Back up photos, files and app data you need. Save account recovery codes somewhere else.
- Finish any pending official Android update and reboot normally before starting.
- Charge above 50% (80% or more is recommended), keep USB connected, and have **20 GB free** on the computer.
- Use a Windows or Linux computer with **Python 3.11 or newer** and **Android SDK Platform-Tools**. Do not run as administrator/root.
- Download the exact official Microsoft recovery ZIP for **Surface Duo 2, 2023.501.541**. Keep it zipped. The helper checks its identity automatically; another version will stop safely.
- Download/extract the complete beta kit from the maintainer. Do not mix files from different releases. Compare the delivered kit's checksum with the maintainer's independently supplied checksum before opening it.

Official downloads: [Python](https://www.python.org/downloads/), [Platform-Tools](https://developer.android.com/tools/releases/platform-tools), [Microsoft recovery images](https://support.microsoft.com/en-us/surface-recovery-image).
Microsoft may require your account and phone serial number. The beta kit combines its data with your own recovery ZIP on your computer; you do not upload that ZIP or your phone keys.

## Optional: get help from an AI assistant

Open [the copy-and-paste assistant prompt](AI-ASSISTANT-PROMPT.txt) and paste its full text into Claude, Codex or another assistant that can inspect local files. Give it access to the extracted kit, **not your private keys**. It starts with a read-only security review before running the installer, then guides you through preparation, phone menus and final checks.

An AI review can miss problems and is not a safety guarantee. Use a kit from the authentic maintainer and verify its independently supplied checksum. Keep PINs, passwords and recovery codes private. You remain in control of phone changes and any data erasure; the assistant must explain and agree the plan with you first.

## Open the helper

**Windows:** extract Platform-Tools and place its `platform-tools` folder beside `Install.cmd`. Double-click **Install.cmd**. If asked, install Python from the official link above, then open the helper again.

**Linux:** extract Platform-Tools alongside the kit. Open a terminal in the kit folder and run **`sh Install.sh`**. If Python's Tk window support is unavailable, the same guided steps run in the terminal. Android USB permissions must already work for your user; do not work around a permission error by running the installer as root.

Select the official Microsoft ZIP and a **new, empty working folder** when asked. File preparation may take several minutes. Keep the helper open until it says **Finished**.

## Updating a compatible beta

1. Unlock Android, connect USB, enable USB debugging and accept this computer's authorization prompt.
2. Open the helper and choose **Update an existing compatible beta**. This flow does not unlock the bootloader or offer a data-format step.
3. Follow the checks. When the helper asks, use the phone's volume buttons and Power to select **Apply update → Apply from ADB**. Continue in the helper when the phone is waiting.
4. Leave USB connected. If recovery asks about installing additional apps, choose **No**. Leave it on the recovery menu until the helper verifies the result and reboots it.
5. Unlock with your existing PIN, continue in the helper and wait for the final checks. Check both screens/touch, RIGHT-side typing, closing/reopening, and your apps/data.

Compatible updates are intended to retain data. Keep a backup anyway. If the installed beta is unsupported or modified, the helper stops rather than switching to an erase flow.

## First installation from stock — erases phone data

1. Start from the supported official stock version above. Complete its setup, enable OEM unlocking and USB debugging in Developer options, and authorize this computer. If OEM unlocking is unavailable, stop and resolve that before trying to install.
2. Open the helper and choose **First installation from supported stock Android**.
3. If the bootloader is locked, the helper explains the erase and requires you to type **ERASE** before requesting an unlock. Confirm the unlock on the phone. It then returns to stock Android; complete its temporary setup and authorize USB debugging again when asked.
4. The helper prepares and boots the owner-authorized temporary recovery. After stock, slot, battery and snapshot checks, it again asks for **ERASE** before the manual data-format step. **First installation requires this data format even if the bootloader was already unlocked.**
5. On the phone choose **Factory reset → Format data/factory reset → Format data**. Wait for success and return to the recovery main menu. Continue in the helper. Do not choose System wipe.
6. Choose **Apply update → Apply from ADB** when prompted. After installation, choose **No** if asked about additional apps and leave the main menu open for verification.
7. Let the helper reboot only after its checks pass. Complete beta setup, enable USB debugging and authorize this computer again. Return to the helper for final verification and the two-minute stability check. If workspace is already active, no extra layout reboot is needed. Otherwise, the helper may offer the independent left/right layout and explain the one normal reboot it needs. This does not erase or reinstall the ROM.

The unlock and first-install data format erase the phone. Accounts, authenticator secrets and some app data may need separate recovery; an ordinary file backup does not cover everything. The helper never handles your PIN or recovery codes.

## If something stops

- **No phone / unauthorized:** unlock normal Android, enable USB debugging and accept the computer prompt. Use a data-capable cable; disconnect other phones if selection is confusing.
- **Bootloader cannot answer:** leave its menu unchanged. Reconnect USB, then consult the maintainer with the session log. Do not repeatedly issue boot commands or change slots.
- **Checks expired:** cancel the waiting sideload screen on the phone and return to recovery's main menu. Use **Check an unfinished or completed installation** and select that session's `state.json`. It refreshes checks if safe. If the battery evidence expired, stop and contact the maintainer for a checked return to normal Android and a fresh session.
- **Progress appears stuck near 47%:** this can be normal while recovery finishes. Check the phone for the additional-apps prompt; choose **No**. Do not unplug USB or reboot while installation is active.
- **Startup messages missing after setup:** do not reinstall. Choose **Check an unfinished or completed installation**, select the same session's `state.json`, then **Reboot once to capture and verify startup**. You can instead choose **Enable independent left/right workspace and reboot once** if you want that layout. The helper verifies the running beta and committed checkpoint first, preserves data, captures the next boot's actual messages and repeats all final checks. It will not repeat a validation reboot automatically.
- **The helper/window was interrupted:** do not start another install. Open **Check an unfinished or completed installation** with the same working folder and session's `state.json`. It never starts a second sender for a session whose sender already began. It can finish verification/reboot when recovery proves success, or finish checks in normal Android after an already verified installation.
- **Signature, hash, slot, snapshot, or security error:** stop. Leave the phone's screen unchanged and keep the session folder. Never accept a signature bypass, choose Enable ADB, manually select a slot, relock, or wipe as a troubleshooting shortcut.

Cancelling a prompt stops the helper; it does not undo a completed unlock, format or installation. During an active transfer, keep the window and USB connection open. A cancelled/stopped phone may remain safely at a bootloader or recovery menu until reviewed.

## Files and privacy

The working folder contains your reconstructed full installer, personalized recovery and local diagnostic sessions. Keep it private, outside a source checkout. Do not upload its contents automatically or share the private `adbkey`; the helper uses only `adbkey.pub` to prepare recovery. Ask the maintainer to identify which logs are needed before sharing anything.

**Prepare files only** performs file assembly, cryptographic checks and recovery preparation with an existing public key. It does not query, reboot, unlock, wipe or flash a phone. Advanced offline invocation:

```text
python -I installer.py --prepare-only --stock PATH_TO_OFFICIAL_ZIP --public-key PATH_TO_ADBKEY.PUB --work NEW_WORK_FOLDER
```

## Supported preview and remaining validation

This kit targets beta **1793400160**. On a fresh installation, setup uses the full display; the independent left/right workspace turns on automatically when setup reaches Home. Use Launcher3 as Home. An existing explicit workspace OFF preference is preserved on update. The recovery fallback remains available. Supported update sources are the matching, unmodified project betas **1793371964** and **1793400160**; arbitrary prototypes, other ROMs, downgrades and unknown signing identities are rejected. Source slot A or B is detected and checked automatically. The owner never selects it.

This is an **experimental community-testing release**. The earlier beta 1793371964 passed fresh setup, default workspace, PIN unlock and recovery fallback on one Duo 2. The clock sizing fix passed 35 targeted emulator checks. This exact release has automated image/signature/emulator validation; it has not been installed on the maintainer phone. **Real Windows, locked-bootloader unlocking and the unlisted hardware features remain untested.** Read TESTING.md, KNOWN-ISSUES.md and RESTORE-STOCK.md before deciding to install. This is not a general-use qualification.

Stock restore and relocking are not buttons in this helper. Beta-to-stock restore/return still needs its own tested procedure and a current backup/data-loss decision; do not treat a stock-to-stock recovery result as proof of a beta rollback path.
