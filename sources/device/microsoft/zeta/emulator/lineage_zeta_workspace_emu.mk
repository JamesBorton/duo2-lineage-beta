# SPDX-License-Identifier: Apache-2.0
# Isolated UI test product: generic x86_64 vendor/kernel, never Duo firmware.
BOARD_EMULATOR_DYNAMIC_PARTITIONS_SIZE := 8589934592
$(call inherit-product, device/generic/goldfish/64bitonly/product/sdk_phone64_x86_64.mk)
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)
PRODUCT_NAME := lineage_zeta_workspace_emu
PRODUCT_MODEL := Zeta Workspace Emulator
PRODUCT_BRAND := LineageOS
PRODUCT_MANUFACTURER := LineageOS
PRODUCT_PACKAGES += Launcher3QuickStep
PRODUCT_PACKAGE_OVERLAYS += device/microsoft/zeta/emulator/overlay
PRODUCT_COPY_FILES += device/microsoft/zeta/emulator/device_state_configuration.xml:$(TARGET_COPY_OUT_VENDOR)/etc/devicestate/device_state_configuration.xml
PRODUCT_COPY_FILES += device/microsoft/zeta/workspace/org.lineageos.zeta.workspace.xml:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/permissions/org.lineageos.zeta.workspace.xml
PRODUCT_ENFORCE_ARTIFACT_PATH_REQUIREMENTS := relaxed

# Only the generic emulator carries this unprivileged UI fixture.
PRODUCT_PACKAGES_DEBUG += ZetaWorkspaceTestApp

# Public OEM Window Extensions library for window-local hinge reporting.
PRODUCT_PACKAGES += androidx.window.extensions

# Exercise the phone setup wizard instead of SDK automatic provisioning.
PRODUCT_PACKAGES += ZetaWorkspaceSetupWizard
