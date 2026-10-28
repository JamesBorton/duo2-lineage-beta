# Source reproduction

This is a reviewed source snapshot for candidate build 1793224122,
not a complete reproducible public binary release. It has a fresh repository
history; original source commit IDs are provenance references, not commits hosted
in this repository. No private bundles or experimental branches are published.

Run `python3 tools/verify-public-tree.py`, then restore into an unused directory:

```sh
python3 tools/restore-sources.py --destination ../zeta-review-sources
```

Linux/WSL is recommended, especially for kernel symlinks. The tool initializes
four source repositories, fetches their exact public base commits, applies the
exported changes to their indexes and checks each resulting Git tree. It copies
the reviewed device/vendor snapshots with their recorded Git modes. Original
custom commit history is intentionally not recreated. Network availability of
the pinned upstream commits remains an external dependency.

The framework, Launcher, kernel and host-only update-engine patches reconstruct
their exact recorded Git trees. Device integration includes the original narrow
HAL adapter and tests. Only three historical local Markdown instructions are
omitted. No generated vendor interface source is required by the new controller.
The vendor snapshot contains integration/staging code, with no firmware binaries.

`manifests/upstream.xml` pins public Android build inputs and omits the six custom
projects. Restore those projects separately. Pinned source commits are
provenance; our private custom commit history is not hosted in this repository.
For an existing Android source root, copy the six restored project directories
to their recorded paths without overwriting unrelated work. `repo sync` does not
install them automatically. Obtain the toolchains in kernel-inputs.json and your
own official stock inputs before building.

Host packaging has one opt-in change in payload_generator/delta_diff_utils.cc:
`ZETA_FULL_REPLACE_BZ2_ONLY=1` chooses standard BZ2/raw/ZERO full operations, which
Python's standard library can reproduce on Windows and Linux. AOSP's separate
`--compressor_types bz2` flag only selects delta compressors. Default host behavior
and the on-device payload consumer are unchanged. The full patch is published.

The current build uses `lunch lineage_zeta-bp4a-userdebug`, `OUT_DIR=out-zeta`,
Clang/toolchain inputs recorded below, and `m -j16 droidcore target-files-package
otatools`. Use a new build number/time for each candidate. Before release, target
files need stock VINTF metadata, complete notice delivery, dedicated signing and
the same package/boot/security audits as the tested candidate. The signing tools
in tools/beta are preparation tools, not an assertion of complete reproduction.

## Kernel and external inputs

The reconstructed kernel includes its zeta_defconfig, public stock module-trust
certificate, Microsoft component lock, imported techpacks/DTs and original notices.
No private signing key is included. MODULE_SIG_FORCE and MODVERSIONS stay enabled.
The public certificate verifies Microsoft's stock modules; it cannot sign new
modules. The baseline is kernel 5.4.233-qgki-c1-p-2023_501_24.

The device's BoardConfigKernel.mk records the Android build flags and toolchain
layout: vendor/zeta_defconfig, Clang r416183b, KERNEL_DEFCONFIG=lahaina-qgki_defconfig,
AZBUILDVER=2023.501.24, and the compatible compiler inputs pinned in kernel-inputs.json.
The expected Image SHA-256 is
387854b5e4fe50e875ab745d72416962564e7f3218caf5d580e684293e82ee5b.
Compiler setup and a full clean-host kernel/ROM rebuild need validation before
claiming complete binary reproduction. Stock GPL module corresponding-source
mapping is separate from reconstruction of our kernel source tree.

The prototype requires official recovery build 2023.501.541. Its ZIP SHA-256 is
8e695f5e7d4a88ee76d06d4457fd6f203f4c65f35aa0c3e0a87961e24ec5c302.
Obtain your own device's recovery package from
[Microsoft](https://support.microsoft.com/surface-recovery-image).
No download mirror, firmware or extraction of third-party inputs is performed by
the source restoration tool. Owner-provided inputs do not by themselves settle
permission to redistribute a resulting binary ROM.
