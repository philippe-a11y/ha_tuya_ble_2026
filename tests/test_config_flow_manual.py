from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1] / "custom_components"


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _Marker:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default

    def __hash__(self):
        return hash(self.key)


class _Schema:
    def __init__(self, schema):
        self.schema = schema


class _Vol:
    Schema = _Schema

    @staticmethod
    def Required(key, default=None):
        return _Marker(key, default)

    @staticmethod
    def Optional(key, default=None):
        return _Marker(key, default)

    @staticmethod
    def In(values):
        return values

    @staticmethod
    def All(*validators):
        return validators

    @staticmethod
    def Length(**kwargs):
        return kwargs


class _BaseFlow:
    def __init_subclass__(cls, **kwargs):
        return super().__init_subclass__()

    def __init__(self):
        self.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(country="LU"),
            data={},
        )
        self.context = {}
        self.unique_id = None

    def async_show_menu(self, *, step_id, menu_options):
        return {"type": "menu", "step_id": step_id, "menu_options": menu_options}

    def async_show_form(self, *, step_id, data_schema, errors, **kwargs):
        result = {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors,
        }
        result.update(kwargs)
        return result

    def async_create_entry(self, *, title, data, options=None):
        result = {"type": "create_entry", "title": title, "data": data}
        if options is not None:
            result["options"] = options
        return result

    def async_abort(self, *, reason):
        return {"type": "abort", "reason": reason}

    async def async_set_unique_id(self, unique_id, **kwargs):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        return None

    def _async_current_ids(self):
        return set()


class _OptionsFlow(_BaseFlow):
    def __init__(self, config_entry):
        super().__init__()
        self.config_entry = config_entry


class _Manager:
    def __init__(self, hass, data):
        self.data = data
        self.build_cache_calls = 0

    async def build_cache(self):
        self.build_cache_calls += 1

    def get_login_from_cache(self):
        return None

    async def get_device_credentials(self, *args, **kwargs):
        return None


class _Discovery:
    def __init__(self):
        self.address = "02-00-00-00-00-01"
        self.name = "TY Coolbox"
        self.device = types.SimpleNamespace(name=self.name)
        self.service_data = {"service": b"data"}


def load_config_flow(discoveries=None):
    for name in list(sys.modules):
        if name == "tuya_ble" or name.startswith("tuya_ble."):
            del sys.modules[name]

    package = _module("tuya_ble")
    package.__path__ = [str(ROOT / "tuya_ble")]

    for module_name in ("const", "manual"):
        spec = importlib.util.spec_from_file_location(
            f"tuya_ble.{module_name}", ROOT / "tuya_ble" / f"{module_name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"tuya_ble.{module_name}"] = module
        spec.loader.exec_module(module)

    _module(
        "voluptuous",
        Schema=_Vol.Schema,
        Required=_Vol.Required,
        Optional=_Vol.Optional,
        In=_Vol.In,
        All=_Vol.All,
        Length=_Vol.Length,
    )
    _module("pycountry", countries=types.SimpleNamespace(get=lambda **kwargs: None))

    class AuthType:
        CUSTOM = "custom"
        SMART_HOME = "smart_home"

    class Endpoint:
        EUROPE = "eu"
        AMERICA = "us"
        INDIA = "in"
        CHINA = "cn"

    _module("tuya_iot", AuthType=AuthType, TuyaCloudOpenAPIEndpoint=Endpoint)

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    _module("homeassistant.const", CONF_ADDRESS="address", CONF_DEVICE_ID="device_id")
    _module("homeassistant.core", callback=lambda function: function)
    _module("homeassistant.data_entry_flow", FlowHandler=_BaseFlow, FlowResult=dict)

    config_entries = _module(
        "homeassistant.config_entries",
        ConfigEntry=object,
        ConfigFlow=_BaseFlow,
        OptionsFlowWithConfigEntry=_OptionsFlow,
    )
    config_entries.__path__ = []

    components = _module("homeassistant.components")
    components.__path__ = []
    bluetooth = _module("homeassistant.components.bluetooth")
    bluetooth.BluetoothServiceInfoBleak = _Discovery
    bluetooth.async_discovered_service_info = lambda hass: list(discoveries or [])

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []

    class TextSelectorType:
        PASSWORD = "password"

    class TextSelectorConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class TextSelector:
        def __init__(self, config):
            self.config = config

    _module(
        "homeassistant.helpers.selector",
        TextSelector=TextSelector,
        TextSelectorConfig=TextSelectorConfig,
        TextSelectorType=TextSelectorType,
    )

    _module(
        "tuya_ble.tuya_ble",
        SERVICE_UUID="service",
        TuyaBLEDeviceCredentials=object,
    )
    async def readable_name(discovery, manager):
        return discovery.name

    _module(
        "tuya_ble.devices",
        TuyaBLEData=object,
        get_device_readable_name=readable_name,
        get_short_address=lambda address: address.replace("-", "")[-6:].upper(),
    )
    _module("tuya_ble.cloud", HASSTuyaBLEDeviceManager=_Manager)

    spec = importlib.util.spec_from_file_location(
        "tuya_ble.config_flow", ROOT / "tuya_ble" / "config_flow.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["tuya_ble.config_flow"] = module
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


class ConfigFlowTests(unittest.TestCase):
    def test_user_step_offers_cloud_and_manual_without_building_cloud_cache(self):
        config_flow = load_config_flow()
        flow = config_flow.TuyaBLEConfigFlow()

        result = asyncio.run(flow.async_step_user())

        self.assertEqual("menu", result["type"])
        self.assertEqual(["login", "manual"], result["menu_options"])
        self.assertIsNone(flow._manager)

    def test_login_form_supplies_tuya_documentation_url(self):
        config_flow = load_config_flow()
        flow = config_flow.TuyaBLEConfigFlow()

        result = asyncio.run(flow.async_step_login())

        self.assertEqual(
            "https://www.home-assistant.io/integrations/tuya/",
            result["description_placeholders"]["tuya_docs_url"],
        )

    def test_discovered_device_opens_manual_form(self):
        discovery = _Discovery()
        config_flow = load_config_flow([discovery])
        flow = config_flow.TuyaBLEConfigFlow()

        result = asyncio.run(flow.async_step_bluetooth(discovery))

        self.assertEqual("form", result["type"])
        self.assertEqual("manual", result["step_id"])
        self.assertIsNone(flow._manager)

    def test_manual_submission_creates_normalized_entry(self):
        discovery = _Discovery()
        config_flow = load_config_flow([discovery])
        flow = config_flow.TuyaBLEConfigFlow()
        flow._discovery_info = discovery

        self.assertTrue(
            hasattr(flow, "async_step_manual"),
            "manual config step has not been implemented",
        )

        result = asyncio.run(flow.async_step_manual(valid_input()))

        self.assertEqual("create_entry", result["type"])
        self.assertEqual(
            {"address": "02:00:00:00:00:01"},
            result["data"],
        )
        self.assertEqual(True, result["options"]["manual_ble_mode"])
        self.assertEqual("Brandson Coolbox", result["title"])

    def test_manual_submission_returns_field_error_for_bad_key(self):
        discovery = _Discovery()
        config_flow = load_config_flow([discovery])
        flow = config_flow.TuyaBLEConfigFlow()
        flow._discovery_info = discovery
        data = valid_input()
        data["local_key"] = "short"

        self.assertTrue(
            hasattr(flow, "async_step_manual"),
            "manual config step has not been implemented",
        )

        result = asyncio.run(flow.async_step_manual(data))

        self.assertEqual("form", result["type"])
        self.assertEqual(
            {"local_key": "invalid_key_length"},
            result["errors"],
        )


class OptionsFlowTests(unittest.TestCase):
    def test_manual_options_preserve_blank_secret_fields(self):
        config_flow = load_config_flow()
        _, options = sys.modules["tuya_ble.manual"].build_manual_entry(valid_input())
        entry = types.SimpleNamespace(
            data={"address": "02:00:00:00:00:01"},
            options=options,
            title="Brandson Coolbox",
            entry_id="entry-id",
        )
        flow = config_flow.TuyaBLEOptionsFlow(entry)
        edited = valid_input()
        edited["local_key"] = ""
        edited["sec_key"] = ""
        edited["device_name"] = "Coolbox Küche"

        result = asyncio.run(flow.async_step_init(edited))

        self.assertEqual("create_entry", result["type"])
        self.assertEqual("abcdefghijklmnop", result["data"]["local_key"])
        self.assertEqual("ponmlkjihgfedcba", result["data"]["sec_key"])
        self.assertEqual("Coolbox Küche", result["data"]["device_name"])


if __name__ == "__main__":
    unittest.main()
