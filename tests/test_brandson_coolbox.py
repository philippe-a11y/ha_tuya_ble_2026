from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "custom_components"
MODULE_PATH = ROOT / "tuya_ble" / "brandson_coolbox.py"


def load_coolbox_module():
    if not MODULE_PATH.exists():
        raise AssertionError("tuya_ble/brandson_coolbox.py has not been implemented")
    spec = importlib.util.spec_from_file_location(
        "tuya_ble.brandson_coolbox", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BrandsonProtocolTests(unittest.TestCase):
    def test_manifest_version_marks_brandson_release(self):
        manifest = json.loads(
            (ROOT / "tuya_ble" / "manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual("0.4.9", manifest["version"])

    def test_verified_datapoint_contract(self):
        coolbox = load_coolbox_module()

        self.assertEqual(("xbx_2b_2", "boagb65r"), (coolbox.CATEGORY, coolbox.PRODUCT_ID))
        self.assertEqual(
            {101, 102, 103, 104, 105, 106, 112, 114, 122, 123},
            {
                coolbox.DP_POWER,
                coolbox.DP_COMPRESSOR,
                coolbox.DP_MODE,
                coolbox.DP_BATTERY_PROTECTION,
                coolbox.DP_TEMPERATURE_UNIT,
                coolbox.DP_FAULT,
                coolbox.DP_CURRENT_TEMPERATURE,
                coolbox.DP_TARGET_TEMPERATURE,
                coolbox.DP_INPUT_VOLTAGE,
                coolbox.DP_BATTERY,
            },
        )

    def test_temperature_conversion_uses_whole_device_degrees(self):
        coolbox = load_coolbox_module()

        self.assertEqual(-14.0, coolbox.device_temperature_to_celsius(-14, 0))
        self.assertEqual(20.0, coolbox.device_temperature_to_celsius(68, 1))
        self.assertEqual(-20, coolbox.celsius_to_device_temperature(-20, 0))
        self.assertEqual(68, coolbox.celsius_to_device_temperature(20, 1))
        self.assertEqual(7, coolbox.celsius_to_device_temperature(-14, 1))

    def test_fault_bitmap_checks_content_not_object_truthiness(self):
        coolbox = load_coolbox_module()

        self.assertFalse(coolbox.bitmap_has_fault(b"\x00"))
        self.assertFalse(coolbox.bitmap_has_fault(bytearray([0, 0])))
        self.assertTrue(coolbox.bitmap_has_fault(b"\x00\x04"))
        self.assertFalse(coolbox.bitmap_has_fault(0))
        self.assertTrue(coolbox.bitmap_has_fault(4))
        self.assertFalse(coolbox.bitmap_has_fault("unexpected"))


if __name__ == "__main__":
    unittest.main()
