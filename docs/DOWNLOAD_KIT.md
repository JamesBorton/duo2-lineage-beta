# Owner-input installer kit

The release ZIP is an assembly kit. It contains the open/project-managed data and
recipes; every stock vendor/ODM/vendor_boot/DTBO operation-data range is withheld.
The owner obtains the exact official Microsoft 2023.501.541 ZIP independently.
Assembly reconstructs the exact beta-signed OTA locally, then checks whole-file,
payload and metadata RSA signatures, hashes and expected partition sizes.

Normal boot/recipes contain no maintainer ADB authorization. Personalized recovery
is generated locally with the owner's existing public adbkey.pub; the private key
never belongs in the kit or a bug report. Full reconstructed OTA, official firmware,
personalized recovery and raw sessions stay local. No automatic upload is needed.

The final release manifest records exact kit/source/checksum identities and the
actual stock-range exclusion/reconstruction result. Windows is still unqualified
for this exact release; older Windows results are not carried forward.
