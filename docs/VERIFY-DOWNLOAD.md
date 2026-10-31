# Verify your download

Download the installer ZIP, SHA256SUMS, SHA256SUMS.sig and beta-signing.x509.pem
from the same release. Keep them together in a new folder. Check the release
number and the certificate fingerprint against a separately obtained project
reference. A checksum from the same compromised download cannot establish trust.

In Windows PowerShell, calculate the ZIP hash:

```powershell
Get-FileHash .\Duo2-beta-installer-1793400160.zip -Algorithm SHA256
```

On Linux:

```sh
sha256sum Duo2-beta-installer-1793400160.zip
```

It must exactly match that filename's line in SHA256SUMS. Do not proceed if it
differs. To verify every downloaded asset on Linux, use `sha256sum --check
--ignore-missing SHA256SUMS`. Missing optional source assets do not stop you from
checking the installer ZIP.

If you have OpenSSL, verify the signing certificate fingerprint and the detached
RSA/SHA256 signature over the entire checksum file:

```sh
openssl x509 -in beta-signing.x509.pem -noout -fingerprint -sha256
openssl x509 -in beta-signing.x509.pem -pubkey -noout -out beta-signing-public.pem
openssl dgst -sha256 -verify beta-signing-public.pem -signature SHA256SUMS.sig SHA256SUMS
```

The expected certificate SHA256 fingerprint (ignoring colons and letter case) is:

`2192dea4f2e70b54b21cd99e8a37083c85aac2a1d7b7ae8066418bbcfdd0bc45`

Expect `Verified OK`. A valid signature proves correspondence to this signing key,
not that the beta is defect-free. The installer independently pins its shipped
files and checks actual OTA signatures before any installation. A failed check is
a stop condition; do not edit checksums, disable verification or run an unknown
replacement helper.
