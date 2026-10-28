# Repository guidance

This is a public source-only beta preparation repository. Read README.md,
LICENSING.md and docs/RELEASE_READINESS.md first. The private development archive
is separate and must not be copied wholesale into this repository.

Preserve existing file licenses and the explicit four-contract omission. Do not
add firmware, APKs, .ko files, private keys, device captures, account data or raw
proprietary disassembly. A reference to an external input is not a license grant.

Run python3 tools/verify-public-tree.py. For source changes, also verify patch
reconstruction against the recorded public bases. CI does not test phone hardware
or establish binary redistribution clearance. Never label an untested ROM ready.
Repository maintenance does not authorize phone wipes, flashing or slot changes.
