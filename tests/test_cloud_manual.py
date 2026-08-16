from __future__ import annotations

import asyncio
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1] / "custom_components"


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def load_cloud_module():
    for name in list(sys.modules):
        if name == "tuya_ble" or name.startswith("tuya_ble."):
            del sys.modules[name]

    package = _module("tuya_ble")
    package.__path__ = [str(ROOT / "tuya_ble")]

    const_spec = importlib.util.spec_from_file_location(
        "tuya_ble.const", ROOT / "tuya_ble" / "const.py"
    )
    assert const_spec is not None and const_spec.loader is not None
    const_module = importlib.util.module_from_spec(const_spec)
    sys.modules["tuya_ble.const"] = const_module
    const_spec.loader.exec_module(const_module)

    @dataclass
    class Credentials:
        uuid: str
        local_key: str
        device_id: str
        category: str
        product_id: str
        device_name: str | None
        product_model: str | None
        product_name: str | None
        ble_user_id: str | None = None

    _module(
        "tuya_ble.tuya_ble",
        AbstaractTuyaBLEDeviceManager=object,
        TuyaBLEDevice=object,
        TuyaBLEDeviceCredentials=Credentials,
    )

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    _module("homeassistant.const", CONF_ADDRESS="address", CONF_DEVICE_ID="device_id")
    _module("homeassistant.core", HomeAssistant=object)
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    _module("homeassistant.helpers.entity", DeviceInfo=object, EntityDescription=object)
    _module(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=object,
        DataUpdateCoordinator=object,
    )

    class AuthType:
        CUSTOM = "custom"
        SMART_HOME = "smart_home"

    _module(
        "tuya_iot",
        TuyaOpenAPI=object,
        AuthType=AuthType,
        TuyaOpenMQ=object,
        TuyaDeviceManager=object,
    )

    cloud_spec = importlib.util.spec_from_file_location(
        "tuya_ble.cloud", ROOT / "tuya_ble" / "cloud.py"
    )
    assert cloud_spec is not None and cloud_spec.loader is not None
    cloud_module = importlib.util.module_from_spec(cloud_spec)
    sys.modules["tuya_ble.cloud"] = cloud_module
    cloud_spec.loader.exec_module(cloud_module)
    return cloud_module, const_module


def manual_data(const) -> dict[str, object]:
    return {
        const.CONF_MANUAL_BLE_MODE: True,
        const.CONF_UUID: "0123456789abcdef",
        const.CONF_LOCAL_KEY: "abcdefghijklmnop",
        "device_id": "device-id",
        const.CONF_CATEGORY: "xbx_2b_2",
        const.CONF_PRODUCT_ID: "boagb65r",
        const.CONF_DEVICE_NAME: "Brandson Coolbox",
        const.CONF_PRODUCT_MODEL: "",
        const.CONF_PRODUCT_NAME: "",
    }


class ManualCloudBypassTests(unittest.TestCase):
    def test_forced_credentials_request_does_not_contact_cloud(self):
        cloud, const = load_cloud_module()
        manager = cloud.HASSTuyaBLEDeviceManager(object(), manual_data(const))
        manager.login = AsyncMock(side_effect=AssertionError("cloud called"))

        credentials = asyncio.run(
            manager.get_device_credentials(
                "02:00:00:00:00:01", force_update=True
            )
        )

        self.assertIsNotNone(credentials)
        self.assertEqual("abcdefghijklmnop", credentials.local_key)
        manager.login.assert_not_awaited()

    def test_incomplete_manual_data_returns_none_without_cloud(self):
        cloud, const = load_cloud_module()
        manager = cloud.HASSTuyaBLEDeviceManager(
            object(), {const.CONF_MANUAL_BLE_MODE: True}
        )
        manager.login = AsyncMock(side_effect=AssertionError("cloud called"))

        credentials = asyncio.run(
            manager.get_device_credentials(
                "02:00:00:00:00:01", force_update=True
            )
        )

        self.assertIsNone(credentials)
        manager.login.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
