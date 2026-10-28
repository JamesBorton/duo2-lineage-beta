# SPDX-License-Identifier: Apache-2.0
TARGET_KERNEL_SOURCE := kernel/microsoft/sm8350
TARGET_KERNEL_CONFIG := vendor/zeta_defconfig
TARGET_KERNEL_CLANG_COMPILE := true
# Match the validated Microsoft build: Clang with the pinned GNU assembler.
TARGET_KERNEL_LLVM_BINUTILS := false
TARGET_KERNEL_CLANG_PATH := $(abspath kernel/microsoft/sm8350-tools/clang/host/linux-x86/clang-r416183b)
KERNEL_TOOLCHAIN := $(abspath kernel/microsoft/sm8350-tools/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/bin)
TARGET_KERNEL_CROSS_COMPILE_PREFIX := aarch64-linux-android-
TARGET_KERNEL_ADDITIONAL_FLAGS += KERNEL_DEFCONFIG=lahaina-qgki_defconfig AZBUILDVER=2023.501.24
TARGET_KERNEL_ADDITIONAL_FLAGS += REAL_CC=$(TARGET_KERNEL_CLANG_PATH)/bin/clang CONFIG_BUILD_ARM64_DT_OVERLAY=y
TARGET_KERNEL_ADDITIONAL_FLAGS += AR=$(TARGET_KERNEL_CLANG_PATH)/bin/llvm-ar NM=$(TARGET_KERNEL_CLANG_PATH)/bin/llvm-nm LLVM_NM=$(TARGET_KERNEL_CLANG_PATH)/bin/llvm-nm
# Retain the stock DTBO/DTB and vendor_boot for the first recovery test.
# Do not set TARGET_NEEDS_DTBOIMAGE: it would rebuild the prebuilt input path.
BOARD_PREBUILT_DTBOIMAGE := vendor/microsoft/zeta/proprietary/images/dtbo.img

# First framework build reuses the source-built, ABI/runtime-validated image.
# Keeping FULL_KERNEL_BUILD false prevents replacing retained stock vendor modules.
TARGET_FORCE_PREBUILT_KERNEL := true
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel/Image
