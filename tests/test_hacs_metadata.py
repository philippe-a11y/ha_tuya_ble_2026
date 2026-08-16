from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "philippe-a11y/ha_tuya_ble_2026"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"


class HACSMetadataTests(unittest.TestCase):
    def test_manifest_points_to_the_published_fork(self):
        manifest = json.loads(
            (
                ROOT
                / "custom_components"
                / "tuya_ble"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual("0.4.9", manifest["version"])
        self.assertEqual(REPOSITORY_URL, manifest["documentation"])
        self.assertEqual(f"{REPOSITORY_URL}/issues", manifest["issue_tracker"])
        self.assertIn("@philippe-a11y", manifest["codeowners"])

    def test_manifest_keys_follow_hassfest_order(self):
        manifest = json.loads(
            (
                ROOT
                / "custom_components"
                / "tuya_ble"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )

        remaining_keys = list(manifest)[2:]
        self.assertEqual(["domain", "name"], list(manifest)[:2])
        self.assertEqual(sorted(remaining_keys), remaining_keys)

    def test_hacs_manifest_and_repository_layout(self):
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))

        self.assertEqual("Tuya BLE", hacs["name"])
        self.assertFalse(hacs["content_in_root"])
        self.assertTrue(
            (ROOT / "custom_components" / "tuya_ble" / "__init__.py").is_file()
        )

    def test_readme_uses_fork_installation_links(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(REPOSITORY_URL, readme)
        self.assertIn("owner=philippe-a11y", readme)
        self.assertIn("repository=ha_tuya_ble_2026", readme)

    def test_validation_workflows_are_present(self):
        workflow_dir = ROOT / ".github" / "workflows"

        self.assertTrue((workflow_dir / "hacs.yml").is_file())
        self.assertTrue((workflow_dir / "hassfest.yml").is_file())

    def test_runtime_uses_stdlib_final(self):
        const_source = (
            ROOT / "custom_components" / "tuya_ble" / "const.py"
        ).read_text(encoding="utf-8")

        self.assertIn("from typing import Final", const_source)
        self.assertNotIn("from typing_extensions import Final", const_source)


if __name__ == "__main__":
    unittest.main()
