# Public beta readiness

As of 2026-10-28: source repository prepared; downloadable beta not released.
The maintainer accepts residual enforcement uncertainty, but a scoped project
license does not resolve missing grants or source/notice obligations.

## Completed for this repository

- Fresh public history with the private archive and raw research omitted.
- Scoped Apache-2.0 grant, retained kernel/upstream terms and third-party notices.
- Exact source pins, payload hashes and independently checked patch reconstruction.
- Four unresolved HAL contracts excluded, with explicit incompleteness recorded.
- No firmware, compiled applications, phone captures or private signing keys.
- Automated source-only/privacy checks and public bug/security reporting guidance.

## Before publishing a ROM

- Resolve or independently replace the four omitted HAL contracts; review the
  actual resulting bindings and shipped controller, not just source filenames.
- Document the applicable basis for every stock component distributed in the
  package, or implement and validate a stock-retaining/owner-input approach.
- Finish GPL corresponding-source/build mapping for distributed modules,
  particularly rmnet_core/ctl/offload/shs. For dual BSD/GPL Wi-Fi modules,
  establish the actual applicable grant and deliver its required notices.
- Reconcile boot-control BSD-Clear metadata, repair and verify legal-notice
  delivery, and verify WebView notices, source correspondence and codec terms.
- Use a documented beta signing setup with protected private keys. The prototype
  uses development/test signing; do not describe it as production release-signed.
  Ensure recovery contains no maintainer-specific ADB authorization.
- Validate a fresh source checkout/build. Publish corresponding source and build
  materials for the exact binary; this source snapshot alone is not that claim.
- Run all current automated ROM/package/boot/security gates and repeat the full
  hardware matrix on the exact release. State untested features explicitly.
- Test the final owner-facing install, update and stock-restore instructions.
  Verify slot/snapshot/partition prerequisites and matching recovery. No relocking.
- Publish checksums, sizes, supported model, minimum stock base, known issues,
  security limitations and rollback instructions alongside the signed assets.

Checksums of a local prototype are not download links or evidence of public
release readiness. No GitHub Release or binary asset is created by this source
preparation. Do not upload the historical private archive as a shortcut.
