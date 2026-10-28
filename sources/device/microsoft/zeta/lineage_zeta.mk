# SPDX-License-Identifier: Apache-2.0
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
TARGET_SUPPORTS_OMX_SERVICE := false
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, device/microsoft/zeta/device.mk)
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)
PRODUCT_NAME := lineage_zeta
PRODUCT_DEVICE := zeta
PRODUCT_MANUFACTURER := Microsoft
PRODUCT_BRAND := Microsoft
PRODUCT_MODEL := Surface Duo 2
