# SPDX-License-Identifier: Apache-2.0
DEVICE_PATH := device/microsoft/zeta
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a-dotprod
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := cortex-a76
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := cortex-a76
TARGET_BOARD_PLATFORM := lahaina
TARGET_BOOTLOADER_BOARD_NAME := surfaceduo2
TARGET_SCREEN_DENSITY := 400
BOARD_BOOT_HEADER_VERSION := 3
BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_KERNEL_CMDLINE := console=ttyMSM0,115200n8 androidboot.console=ttyMSM0 androidboot.memcg=1 lpm_levels.sleep_disabled=1 video=vfb:640x400,bpp=32,memsize=3072000 msm_rtb.filter=0x237 service_locator.enable=1 androidboot.usbcontroller=a600000.dwc3 swiotlb=0 loop.max_part=7 cgroup.memory=nokmem,nosocket pcie_ports=compat iptable_raw.raw_before_defrag=1 ip6table_raw.raw_before_defrag=1 androidboot.hardware=surfaceduo2 androidboot.hardware.platform=qcom buildvariant=user
BOARD_MKBOOTIMG_ARGS += --header_version 3
BOARD_BOOTIMAGE_PARTITION_SIZE := 134217728
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_DTBOIMG_PARTITION_SIZE := 25165824
BOARD_FLASH_BLOCK_SIZE := 262144
BOARD_USES_RECOVERY_AS_BOOT := true
BOARD_USES_METADATA_PARTITION := true
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_ODM := odm
TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_SUPER_PARTITION_SIZE := 15032385536
BOARD_SUPER_PARTITION_GROUPS := surface_dynamic_partitions
BOARD_SURFACE_DYNAMIC_PARTITIONS_SIZE := 7511998464
BOARD_SURFACE_DYNAMIC_PARTITIONS_PARTITION_LIST := system system_ext product vendor odm
# Live LP geometry has three slots and 64KiB metadata; lpmake selects three slots for A/B.
BOARD_AVB_ENABLE := true
DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE := $(DEVICE_PATH)/framework_compatibility_matrix.xml
include $(DEVICE_PATH)/BoardConfigKernel.mk
include vendor/microsoft/zeta/BoardConfigVendor.mk

# Recovery combines platform and this narrowly scoped device policy.
BOARD_VENDOR_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/vendor

# Keep the final stock vendor_boot payload; the build regenerates its AVB footer.
BOARD_PREBUILT_VENDOR_BOOTIMAGE := vendor/microsoft/zeta/proprietary/images/vendor_boot.img
BOARD_SUPER_PARTITION_ALIGNMENT := 524288
# Stock physical alignment offset is 499712. OTA operations preserve live geometry;
# super_empty is a diagnostic artifact until offset handling is independently verified.
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_SYSTEM_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA4096
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := 0
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 2
# Stock SKU manifest is installed unchanged; checker SKU is declared in Android.mk.
DEVICE_MATRIX_FILE := vendor/microsoft/zeta/proprietary/vendor/etc/vintf/compatibility_matrix.xml

# Recovery and runtime update services use the standard A/B workflow.
AB_OTA_UPDATER := true

# Normal Android AIDL QTI boot control; stock vendor remains unchanged.
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/system_ext/private
