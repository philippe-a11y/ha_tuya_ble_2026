"""Verified datapoint contract for the Brandson Coolbox."""
from __future__ import annotations


CATEGORY = "xbx_2b_2"
PRODUCT_ID = "boagb65r"

DP_POWER = 101
DP_COMPRESSOR = 102
DP_MODE = 103
DP_BATTERY_PROTECTION = 104
DP_TEMPERATURE_UNIT = 105
DP_FAULT = 106
DP_CURRENT_TEMPERATURE = 112
DP_TARGET_TEMPERATURE = 114
DP_INPUT_VOLTAGE = 122
DP_BATTERY = 123

UNIT_CELSIUS = 0
UNIT_FAHRENHEIT = 1
TARGET_MIN_C = -20.0
TARGET_MAX_C = 20.0
TARGET_STEP_C = 1.0


def device_temperature_to_celsius(value: float, unit: int) -> float:
    """Convert a device display temperature to Home Assistant Celsius."""
    if unit == UNIT_FAHRENHEIT:
        return (value - 32.0) * 5.0 / 9.0
    return float(value)


def celsius_to_device_temperature(value: float, unit: int) -> int:
    """Convert Home Assistant Celsius to the device's whole-degree unit."""
    converted = value * 9.0 / 5.0 + 32.0 if unit == UNIT_FAHRENHEIT else value
    return round(converted)


def bitmap_has_fault(value: object) -> bool:
    """Return whether at least one bit in a Tuya bitmap value is set."""
    if isinstance(value, (bytes, bytearray)):
        return any(value)
    if isinstance(value, int):
        return value != 0
    return False
