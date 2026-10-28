# SPDX-License-Identifier: Apache-2.0
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)
PRODUCT_SHIPPING_API_LEVEL := 30
AB_OTA_PARTITIONS += boot dtbo odm product system system_ext vbmeta vbmeta_system vendor vendor_boot
TARGET_OTA_ASSERT_DEVICE := zeta,duo2
# Linux 5.4 lacks MREMAP_DONTUNMAP, required by ART userfaultfd GC.
PRODUCT_ENABLE_UFFD_GC := false
PRODUCT_USE_DYNAMIC_PARTITIONS := true
# The actual VNDK 30 snapshot is pinned in zeta.xml; retain the vendor ABI.
PRODUCT_EXTRA_VNDK_VERSIONS += 30
PRODUCT_SOONG_NAMESPACES += vendor/microsoft/zeta hardware/qcom-caf/bootctrl
PRODUCT_AAPT_CONFIG := normal
PRODUCT_AAPT_PREF_CONFIG := 400dpi
# First full ROM: retain raw stock vendor/ODM and stock vendor_boot payload.
PRODUCT_BUILD_SUPER_PARTITION := false
PRODUCT_BUILD_SUPER_EMPTY_IMAGE := false
PRODUCT_BUILD_USERDATA_IMAGE := false
PRODUCT_BUILD_INIT_BOOT_IMAGE := false
PRODUCT_BUILD_VENDOR_BOOT_IMAGE := false
PRODUCT_ENFORCE_VINTF_MANIFEST := true
# Raw vendor has no matching new precompiled policy; init compiles stock CIL with framework mappings.
PRODUCT_PRECOMPILED_SEPOLICY := false
# Stock QTI boot control manages GPT slot attributes, not generic misc-only A/B state.
PRODUCT_PACKAGES += android.hardware.boot-service.qti.recovery zeta-slot-status
$(call inherit-product, vendor/microsoft/zeta/zeta-vendor.mk)

# Stock BSD-licensed recovery setup: configfs USB controller and bootdevice link.
PRODUCT_COPY_FILES += \
    device/microsoft/zeta/recovery/init.recovery.surfaceduo2.rc:$(TARGET_COPY_OUT_RECOVERY)/root/init.recovery.surfaceduo2.rc

# Standard A/B updater stack, including the recovery installer and boot verifier.
PRODUCT_PACKAGES += \
    update_engine \
    update_engine_sideload \
    update_verifier
PRODUCT_PACKAGES_DEBUG += update_engine_client

# OEM device-state extension avoids modifying the retained raw vendor image.
PRODUCT_PACKAGES += zeta-device-state
PRODUCT_SYSTEM_SERVER_JARS += zeta-device-state
# Product overlay stays outside the retained raw vendor image.
PRODUCT_PACKAGE_OVERLAYS += device/microsoft/zeta/overlay

# Automatic posture controller runs as ordinary platform_app, not shared system UID.
PRODUCT_PACKAGES += ZetaPostureController
PRODUCT_COPY_FILES += device/microsoft/zeta/posture/permissions/org.lineageos.zeta.posture.xml:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/permissions/org.lineageos.zeta.posture.xml

# Android 16 boot-success recording requires a modern normal-boot HAL.
PRODUCT_PACKAGES += android.hardware.boot-service.zeta zeta-slot-status-android

# Standard restricted boot-control diagnostic client for userdebug maintenance.
PRODUCT_PACKAGES_DEBUG += bootctl

# Workspace code is present but opt-in; legacy behavior remains the default.
PRODUCT_COPY_FILES += device/microsoft/zeta/workspace/org.lineageos.zeta.workspace.xml:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/permissions/org.lineageos.zeta.workspace.xml

# Public OEM Window Extensions library for window-local hinge reporting.
PRODUCT_PACKAGES += androidx.window.extensions
