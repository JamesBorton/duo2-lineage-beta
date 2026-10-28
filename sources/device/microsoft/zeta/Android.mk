# SPDX-License-Identifier: Apache-2.0
# Lineage's default kernel prefix handles only OUT_DIR=out. The zeta build
# uses a separate relative directory to preserve the reference outputs.
# This file is read before vendor/lineage/build/tasks/kernel.mk.
ifneq ($(filter /%,$(OUT_DIR)),)
KERNEL_BUILD_OUT_PREFIX :=
else
KERNEL_BUILD_OUT_PREFIX := $(BUILD_TOP)/
endif

# Raw API-30 vendor: the generic SKU assembler insists on current policy version.
# Install the unmodified XML via prebuilt_etc, then declare its SKU for Make's
# VINTF checks and OTA metadata after android-info.mk has been read.
DEVICE_MANIFEST_SKUS := lahaina
