# Source reproduction

This is a reviewed source snapshot associated with prototype build 1793208198,
not a complete reproducible public binary release. It has a fresh repository
history; original source commit IDs are provenance references, not commits hosted
in this repository. No private bundles or experimental branches are published.

Run `python3 tools/verify-public-tree.py`, then restore into an unused directory:

```sh
python3 tools/restore-sources.py --destination ../zeta-review-sources
```

Linux/WSL is recommended, especially for kernel symlinks. The tool initializes
three source repositories, fetches their exact public base commits, applies the
exported changes to their indexes and checks each resulting Git tree. It copies
the reviewed device/vendor snapshots with their recorded Git modes. Original
custom commit history is intentionally not recreated. Network availability of
the pinned upstream commits remains an external dependency.

The framework, Launcher and kernel patches each reconstruct their recorded
prototype Git tree. The device snapshot deliberately excludes four HAL contracts
and historical local documentation, recorded individually in source-snapshot.json.
The vendor snapshot is exact, source-only integration code. These partial sources
cannot currently build the physical phone product: the controller references the
missing HIDL-generated interfaces. The tool does not silently download them.

`manifests/upstream.xml` pins the public Android build inputs and omits the five
custom projects. It contains no local/private Git remotes. It is a dependency lock,
not an instruction to run a partial phone build. The source tool restores custom
projects separately; running `repo sync` does not install those projects itself.

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
