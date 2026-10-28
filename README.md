# LineageOS for Surface Duo 2

Unofficial LineageOS 23.2 / Android 16 work for **Surface Duo 2 (zeta / SM8350)**.
Independent community project; not affiliated with or endorsed by Microsoft,
Qualcomm or the LineageOS project. Surface Duo 1 is not a supported target.

**Status: public beta preparation. No installable ROM or recovery is published here yet.**
This repository publishes a reviewed source snapshot, known issues and release
requirements. The new beta candidate replaces four copied HAL contracts with an original narrow
AOSP HwBinder adapter. All 25 current-source emulator gates pass; its exact signed
phone build and owner-input download kit are still being verified.
The planned download is an assembly kit: each owner supplies the official Microsoft
recovery ZIP, then the kit reconstructs the complete signed installer locally.
See [download design](docs/DOWNLOAD_KIT.md), [release readiness](docs/RELEASE_READINESS.md) and [installation status](docs/INSTALLATION.md).

## Prototype behavior

The maintainer's prototype boots with SELinux Enforcing. Owner testing across
recent candidates has confirmed both displays and touch, independent apps,
shared Recents, app toss, This screen / Other screen buttons, folded screen
switching, a keyboard on either panel and right-default unlock controls.
Build 1793208198 additionally passed prompt close-to-sleep and reopen/touch tests
on USB and battery. Wi-Fi and front/rear camera previews passed on earlier builds;
the full hardware smoke test has not been repeated on this exact build.

This is not a claim of daily-driver readiness. Cellular, fingerprint, Bluetooth,
audio, long-term battery behavior and other hardware need a published acceptance
matrix. Pen and peek/glance support are deferred. Android 11 vendor components
and a 5.4.233 kernel remain; no new kernel security backports are claimed.

## Sources and checks

| Location | Contents |
|---|---|
| `patches/` | Framework, Launcher, kernel and host packaging changes against exact public bases; no private Git history |
| `sources/` | Device and vendor integration source, including the new HAL adapter; historical local instructions omitted |
| `manifests/source-snapshot.json` | Original revisions, expected reconstructed trees, SHA-256 values and explicit omissions |
| `manifests/upstream.xml` | Pinned public upstream Android dependencies; custom projects are restored separately |
| `manifests/kernel-inputs.json` | Microsoft component and compiler input revisions |
| `LICENSES/` | Applicable license texts and kernel licensing information |

With Python 3.11+ and Git:

```sh
python3 tools/verify-public-tree.py
python3 tools/restore-sources.py --destination ../zeta-review-sources
```

The second command downloads pinned public source bases into a **new** directory,
applies the patches and verifies the reconstructed trees. It does not fetch
firmware, signing keys or compiler tools, and does not build or flash
a phone. Read [source reproduction](docs/SOURCES.md) first.

## Licensing and participation

Our eligible original contributions are Apache-2.0. Kernel and third-party
material keep their existing licenses; this is a mixed-license repository.
Read [licensing scope](LICENSING.md), [third-party notices](THIRD_PARTY_NOTICES.md)
and [NOTICE](NOTICE). No license to Microsoft/Qualcomm stock firmware is granted
by this project's Apache license. No firmware or built applications are included.

See [contribution guidance](CONTRIBUTING.md) and [security reporting](SECURITY.md).
For a rights or attribution concern, open an issue identifying the affected path
and ownership/basis. Please omit private credentials and device identifiers.
Software is supplied as-is under the applicable license terms.
