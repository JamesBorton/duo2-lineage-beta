# Contributing

Report the exact build/revision, affected panel/posture, reproducible steps and
expected/actual result. State whether a result was observed on real hardware or
an emulator. Do not include PINs, credentials, device serials or unredacted dumps.

Submit original contributions under Apache-2.0 where the project license applies.
Changes to kernel or other third-party files retain their existing applicable
licenses. Preserve upstream copyright and NOTICE information. Do not contribute
firmware, APKs, leaked source, decompiled proprietary implementations or code
whose redistribution basis you cannot identify. A contributor can grant only
rights they hold; no blanket relicensing of others' work is requested.

Run `python3 tools/verify-public-tree.py` before a pull request. Any change to an
exported checkpoint needs an updated manifest and source reconstruction evidence.
Do not hand-edit immutable checkpoint patches merely to make a hash check pass.
New snapshots should record their real source revisions and provenance.
