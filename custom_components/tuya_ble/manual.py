"""Helpers for cloud-free Tuya BLE configuration."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_CATEGORY,
    CONF_DEVICE_NAME,
    CONF_LOCAL_KEY,
    CONF_MANUAL_BLE_MODE,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_MODEL,
    CONF_PRODUCT_NAME,
    CONF_SEC_KEY,
    CONF_UUID,
)

CONF_ADDRESS = "address"
CONF_DEVICE_ID = "device_id"


def _effective_secret(
    user_input: dict[str, Any],
    existing_options: dict[str, Any] | None,
    key: str,
) -> str:
    """Return a submitted secret or preserve the saved value on edit."""
    value = user_input.get(key, "")
    if value == "" and existing_options is not None:
        return str(existing_options.get(key, ""))
    return str(value)


def validate_manual_input(
    user_input: dict[str, Any],
    *,
    existing_options: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Validate Tuya keys by encoded byte length."""
    errors: dict[str, str] = {}
    local_key = _effective_secret(user_input, existing_options, CONF_LOCAL_KEY)
    sec_key = _effective_secret(user_input, existing_options, CONF_SEC_KEY)

    for key in (
        CONF_ADDRESS,
        CONF_DEVICE_NAME,
        CONF_DEVICE_ID,
        CONF_UUID,
        CONF_CATEGORY,
        CONF_PRODUCT_ID,
    ):
        if not str(user_input.get(key, "")).strip():
            errors[key] = "required"

    if len(local_key.encode("utf-8")) != 16:
        errors[CONF_LOCAL_KEY] = "invalid_key_length"
    if sec_key and len(sec_key.encode("utf-8")) != 16:
        errors[CONF_SEC_KEY] = "invalid_key_length"

    return errors


def normalize_address(address: str) -> str:
    """Normalize a Bluetooth address for config-entry identity."""
    return address.replace("-", ":").upper()


def build_manual_entry(
    user_input: dict[str, Any],
    *,
    existing_options: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build normalized config-entry data from validated manual input."""
    errors = validate_manual_input(
        user_input,
        existing_options=existing_options,
    )
    if errors:
        raise ValueError(errors)

    address = normalize_address(str(user_input[CONF_ADDRESS]))
    options = {
        CONF_MANUAL_BLE_MODE: True,
        CONF_UUID: str(user_input[CONF_UUID]).strip(),
        CONF_LOCAL_KEY: _effective_secret(
            user_input, existing_options, CONF_LOCAL_KEY
        ),
        CONF_SEC_KEY: _effective_secret(user_input, existing_options, CONF_SEC_KEY),
        CONF_DEVICE_ID: str(user_input[CONF_DEVICE_ID]).strip(),
        CONF_CATEGORY: str(user_input[CONF_CATEGORY]).strip(),
        CONF_PRODUCT_ID: str(user_input[CONF_PRODUCT_ID]).strip(),
        CONF_DEVICE_NAME: str(user_input[CONF_DEVICE_NAME]).strip(),
        CONF_PRODUCT_MODEL: "",
        CONF_PRODUCT_NAME: "",
    }
    return address, options
