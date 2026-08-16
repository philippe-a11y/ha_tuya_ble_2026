from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1] / "custom_components"
MODULE_PATH = ROOT / "tuya_ble" / "manual.py"


def load_manual_module():
    if not MODULE_PATH.exists():
        raise AssertionError("tuya_ble/manual.py has not been implemented")

    package = types.ModuleType("tuya_ble")
    package.__path__ = [str(ROOT / "tuya_ble")]
    sys.modules["tuya_ble"] = package

    const_path = ROOT / "tuya_ble" / "const.py"
    const_spec = importlib.util.spec_from_file_location("tuya_ble.const", const_path)
    assert const_spec is not None and const_spec.loader is not None
    const_module = importlib.util.module_from_spec(const_spec)
    sys.modules["tuya_ble.const"] = const_module
    const_spec.loader.exec_module(const_module)

    spec = importlib.util.spec_from_file_location("tuya_ble.manual", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["tuya_ble.manual"] = module
    spec.loader.exec_module(module)
    return module


def valid_input() -> dict[str, str]:
    return {
        "address": "02-00-00-00-00-01",
        "device_name": "Brandson Coolbox",
        "device_id": "device-id",
        "uuid": "0123456789abcdef",
        "local_key": "abcdefghijklmnop",
        "sec_key": "ponmlkjihgfedcba",
        "category": "xbx_2b_2",
        "product_id": "boagb65r",
    }


class ManualValidationTests(unittest.TestCase):
    def test_valid_input_has_no_errors(self):
        manual = load_manual_module()

        self.assertEqual({}, manual.validate_manual_input(valid_input()))

    def test_local_key_requires_exactly_16_utf8_bytes(self):
        manual = load_manual_module()

        for invalid_key in ("short", "12345678901234567", "ä" * 16):
            with self.subTest(invalid_key=invalid_key):
                data = valid_input()
                data["local_key"] = invalid_key
                self.assertEqual(
                    {"local_key": "invalid_key_length"},
                    manual.validate_manual_input(data),
                )

    def test_sec_key_is_optional_but_validated_when_present(self):
        manual = load_manual_module()
        data = valid_input()
        data["sec_key"] = ""
        self.assertEqual({}, manual.validate_manual_input(data))

        data["sec_key"] = "too-short"
        self.assertEqual(
            {"sec_key": "invalid_key_length"},
            manual.validate_manual_input(data),
        )

    def test_required_identifiers_reject_whitespace_only_values(self):
        manual = load_manual_module()
        data = valid_input()
        data["product_id"] = "   "

        self.assertEqual(
            {"product_id": "required"},
            manual.validate_manual_input(data),
        )

    def test_options_are_normalized_and_complete(self):
        manual = load_manual_module()
        data = valid_input()
        data["device_name"] = "  Brandson Coolbox  "

        address, options = manual.build_manual_entry(data)

        self.assertEqual("02:00:00:00:00:01", address)
        self.assertEqual(True, options["manual_ble_mode"])
        self.assertEqual("Brandson Coolbox", options["device_name"])
        self.assertEqual("abcdefghijklmnop", options["local_key"])
        self.assertEqual("ponmlkjihgfedcba", options["sec_key"])
        self.assertEqual("", options["product_model"])
        self.assertEqual("", options["product_name"])

    def test_blank_option_keys_preserve_saved_secrets(self):
        manual = load_manual_module()
        current = manual.build_manual_entry(valid_input())[1]
        edited = valid_input()
        edited["local_key"] = ""
        edited["sec_key"] = ""
        edited["device_name"] = "New Name"

        errors = manual.validate_manual_input(edited, existing_options=current)
        _, options = manual.build_manual_entry(edited, existing_options=current)

        self.assertEqual({}, errors)
        self.assertEqual("abcdefghijklmnop", options["local_key"])
        self.assertEqual("ponmlkjihgfedcba", options["sec_key"])
        self.assertEqual("New Name", options["device_name"])


if __name__ == "__main__":
    unittest.main()
