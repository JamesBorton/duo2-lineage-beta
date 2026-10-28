# Security and support

This is an experimental source project. No public binary version is currently
supported. Old vendor/kernel components and development signing are known
prototype limitations; do not infer a current security patch level from Android 16.

For a vulnerability containing sensitive details, use this repository's private
[security reporting](https://github.com/JamesBorton/duo2-lineage-beta/security/advisories/new).
Ordinary bugs and attribution/rights concerns can be filed as issues. No response
time, updates or long-term support commitment is promised.

Never submit signing keys, ADB private keys, unlock credentials, recovery serial
numbers, personal content, account tokens or complete unredacted device logs.

Beta preparation uses dedicated protected APK/APEX/OTA/AVB keys. The actual
candidate signatures are checked independently, including embedded APEX APKs and
MAC signer policy. The upstream CTS APEX test shim is an explicit preserved AOSP
exception, and WebView retains its exact upstream signature. These facts do not
make this a hardened production device. It remains an unlocked userdebug build,
with Android11 vendor code and Linux5.4.233. A framework patch date does not make
the vendor/kernel current. No new kernel security backports are claimed.

Public recovery inputs contain no maintainer ADB authorization. Owner preparation
adds only the owner's existing public key while keeping authentication enabled.
Never upload your personalized recovery, private keys or unredacted preflight logs
as a project release asset. Project OTA certificates contain public keys only.
