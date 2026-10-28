# Licensing scope

Copyright 2026 James Borton and the respective project contributors.

The Apache License 2.0 in LICENSE applies to this project's eligible original
documentation, tools, device/vendor integration code and original contributions
to the framework and launcher. It grants only rights held by the applicable
contributors. It does not relicense third-party work or clear unresolved rights.

Existing file headers, SPDX identifiers and upstream license/NOTICE files govern
imported content. An Apache default does not override a more specific license.
In particular:

- `patches/frameworks-base.patch` and `patches/launcher3.patch`: existing AOSP and
  LineageOS notices remain; project-original modifications use Apache-2.0.
- `patches/kernel-sm8350.patch.gz`: Linux GPL-2.0-only with Linux-syscall-note
  where applicable, plus existing file-specific licenses in the imported
  Microsoft/Qualcomm techpacks and device trees. Our kernel modifications follow
  the applicable kernel/file license; the Apache default does not apply to them.
- `sources/device/microsoft/zeta/bootctrl/`: imported AOSP, Linux Foundation and
  Qualcomm code retains Apache-2.0, BSD-3-Clause and BSD-3-Clause-Clear terms as
  indicated by its headers. Full texts and provenance are provided separately.
- `sources/device/microsoft/zeta/posture/`: original controller/classifier code
  uses Apache-2.0. The four third-party `.hal` contracts are not included.
- `sources/vendor/microsoft/zeta/`: project integration/staging source only;
  references to external stock inputs do not license those inputs.
- `LICENSES/`: copies of existing license documents retain their own notices.

No stock ROM, vendor/ODM image, vendor_boot/DTBO payload, `.ko`, APK, proprietary
library or private key is distributed here. Their rights are not granted by this
repository. A public binary release requires its own component and source review.
The public source snapshot does not establish GPL compliance for any separate ROM.

Microsoft, Surface, Qualcomm, Android and LineageOS names identify compatibility
and provenance. No trademark rights, certification or endorsement are granted.
Warranty and liability terms are those of each applicable license, subject to law.
