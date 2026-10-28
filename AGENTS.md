# Repository guidance

This is the public beta preparation repository. Read README.md, LICENSING.md and
docs/RELEASE_READINESS.md first. Preserve file-specific licenses. The private
archive, old contracts and diagnostic research must not be copied wholesale.

Four old contracts are retired, with their removal recorded in the source
manifest. The new narrow transport source and tests are published. Do not restore
the old HIDL declarations or generated vendor Java classes.

Do not add stock firmware, APKs, .ko files, private keys, device captures, account
data or proprietary disassembly to Git. The planned owner-input release kit must
exclude every stock partition's payload data range and reconstruct a verified
byte-identical signed installer. An input reference grants no firmware rights.

Run tools/verify-public-tree.py, the assembler's test_assembly.py, and verify patch
reconstruction against the recorded bases after source changes. CI does not
establish phone hardware acceptance or a legal clearance. Never label an untested
ROM ready. Repository maintenance does not authorize wipes or phone operations.
