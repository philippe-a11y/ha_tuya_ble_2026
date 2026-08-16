from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "tuya_ble"
)


class TranslationTests(unittest.TestCase):
    def test_brandson_entity_text_is_complete(self):
        required = {
            "climate": {"coolbox"},
            "sensor": {"input_voltage", "battery"},
            "binary_sensor": {"compressor_running", "fault"},
            "select": {
                "operating_mode",
                "battery_protection",
                "temperature_unit",
            },
        }

        for path in (ROOT / "strings.json", ROOT / "translations" / "en.json"):
            with self.subTest(path=path.name):
                entities = json.loads(path.read_text(encoding="utf-8"))["entity"]
                for platform, keys in required.items():
                    self.assertLessEqual(keys, set(entities.get(platform, {})))

                self.assertEqual(
                    {"max": "MAX", "eco": "ECO"},
                    entities["select"]["operating_mode"]["state"],
                )
                self.assertEqual(
                    {"low": "Low", "medium": "Medium", "high": "High"},
                    entities["select"]["battery_protection"]["state"],
                )

    def test_manual_config_and_options_text_is_complete(self):
        for path in (ROOT / "strings.json", ROOT / "translations" / "en.json"):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                config = data["config"]
                self.assertIn("user", config["step"])
                self.assertEqual(
                    {"login": "Tuya Cloud", "manual": "Manual BLE device"},
                    config["step"]["user"]["menu_options"],
                )
                self.assertEqual(
                    "The key must contain exactly 16 UTF-8 bytes.",
                    config["error"]["invalid_key_length"],
                )
                self.assertIn("required", config["error"])
                self.assertEqual(
                    "This field is required.",
                    config["error"]["required"],
                )
                self.assertIn("manual", config["step"])
                self.assertIn("local_key", config["step"]["manual"]["data"])
                self.assertIn("sec_key", config["step"]["manual"]["data"])
                self.assertIn("manual", data["options"]["step"])

    def test_login_description_uses_a_url_placeholder(self):
        for path in (ROOT / "strings.json", ROOT / "translations" / "en.json"):
            with self.subTest(path=path.name):
                description = json.loads(path.read_text(encoding="utf-8"))[
                    "config"
                ]["step"]["login"]["description"]

                self.assertNotIn("https://", description)
                self.assertIn("{tuya_docs_url}", description)


if __name__ == "__main__":
    unittest.main()
