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


class _Description:
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.translation_key = kwargs.pop("translation_key", None)
        for name, value in kwargs.items():
            setattr(self, name, value)


class _Coordinator:
    @classmethod
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, *args, **kwargs):
        self.connected = True


class _TuyaBLEEntity:
    def __init__(self, hass, coordinator, device, product, description):
        self._hass = hass
        self._coordinator = coordinator
        self._device = device
        self._product = product
        self.entity_description = description
        self._attr_supported_features = 0

    def async_write_ha_state(self):
        return None


class _FakeDataPoint:
    def __init__(self, dp_id, dp_type, value, timestamp=0):
        self.id = dp_id
        self.type = dp_type
        self.value = value
        self.timestamp = timestamp
        self.last_set_value = None

    async def set_value(self, value):
        self.last_set_value = value
        self.value = value


class _FakeDataPoints:
    def __init__(self):
        self._items = {}

    def __getitem__(self, dp_id):
        return self._items.get(dp_id)

    def set(self, dp_id, dp_type, value, timestamp=0):
        item = _FakeDataPoint(dp_id, dp_type, value, timestamp)
        self._items[dp_id] = item
        return item

    def get_or_create(self, dp_id, dp_type, value):
        item = self._items.get(dp_id)
        if item is None:
            item = self.set(dp_id, dp_type, value)
        return item


class _FakeDevice:
    def __init__(self, category="xbx_2b_2", product_id="boagb65r"):
        self.category = category
        self.product_id = product_id
        self.datapoints = _FakeDataPoints()


class _FakeHass:
    def __init__(self):
        self.tasks = []

    def create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


def _clear_tuya_modules():
    for name in list(sys.modules):
        if name == "tuya_ble" or name.startswith("tuya_ble."):
            del sys.modules[name]


def _load_source(module_name: str, relative_path: str):
    path = ROOT / "tuya_ble" / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_climate_module():
    _clear_tuya_modules()
    package = _module("tuya_ble")
    package.__path__ = [str(ROOT / "tuya_ble")]
    _load_source("tuya_ble.brandson_coolbox", "brandson_coolbox.py")

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    components = _module("homeassistant.components")
    components.__path__ = []

    class ClimateEntity:
        pass

    _module(
        "homeassistant.components.climate",
        ClimateEntityDescription=_Description,
        ClimateEntity=ClimateEntity,
    )

    class ClimateEntityFeature:
        PRESET_MODE = 1
        TARGET_TEMPERATURE = 2
        TARGET_HUMIDITY = 4

    class HVACMode:
        OFF = "off"
        HEAT = "heat"
        COOL = "cool"

    class HVACAction:
        OFF = "off"
        IDLE = "idle"
        HEATING = "heating"
        COOLING = "cooling"

    _module(
        "homeassistant.components.climate.const",
        ClimateEntityFeature=ClimateEntityFeature,
        HVACMode=HVACMode,
        HVACAction=HVACAction,
        PRESET_AWAY="away",
        PRESET_NONE="none",
    )
    _module("homeassistant.config_entries", ConfigEntry=object)

    class UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"

    _module("homeassistant.const", UnitOfTemperature=UnitOfTemperature)
    _module("homeassistant.core", HomeAssistant=object, callback=lambda function: function)
    _module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=_Coordinator,
    )
    _module("tuya_ble.const", DOMAIN="tuya_ble")
    _module(
        "tuya_ble.devices",
        TuyaBLEData=object,
        TuyaBLEEntity=_TuyaBLEEntity,
        TuyaBLEProductInfo=object,
    )

    class TuyaBLEDataPointType:
        DT_BOOL = "bool"
        DT_VALUE = "value"
        DT_ENUM = "enum"

    _module(
        "tuya_ble.tuya_ble",
        TuyaBLEDataPoint=_FakeDataPoint,
        TuyaBLEDataPointType=TuyaBLEDataPointType,
        TuyaBLEDevice=_FakeDevice,
    )
    return _load_source("tuya_ble.climate", "climate.py")


def load_devices_module():
    _clear_tuya_modules()
    package = _module("tuya_ble")
    package.__path__ = [str(ROOT / "tuya_ble")]
    _load_source("tuya_ble.brandson_coolbox", "brandson_coolbox.py")

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    _module(
        "homeassistant.const",
        CONF_ADDRESS="address",
        CONF_DEVICE_ID="device_id",
    )
    _module(
        "homeassistant.core",
        CALLBACK_TYPE=object,
        HomeAssistant=object,
        callback=lambda function: function,
    )
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    _module(
        "homeassistant.helpers.device_registry",
        CONNECTION_BLUETOOTH="bluetooth",
    )
    _module(
        "homeassistant.helpers.entity",
        DeviceInfo=dict,
        EntityDescription=_Description,
    )
    _module(
        "homeassistant.helpers.event",
        async_call_later=lambda *args, **kwargs: None,
    )

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    _module(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=CoordinatorEntity,
        DataUpdateCoordinator=_Coordinator,
    )
    _module(
        "home_assistant_bluetooth",
        BluetoothServiceInfoBleak=object,
    )
    _module(
        "tuya_ble.tuya_ble",
        AbstaractTuyaBLEDeviceManager=object,
        TuyaBLEDataPoint=_FakeDataPoint,
        TuyaBLEDevice=_FakeDevice,
        TuyaBLEDeviceCredentials=object,
    )
    _module("tuya_ble.cloud", HASSTuyaBLEDeviceManager=object)
    _module(
        "tuya_ble.const",
        DEVICE_DEF_MANUFACTURER="Tuya",
        DOMAIN="tuya_ble",
        FINGERBOT_BUTTON_EVENT="event",
        SET_DISCONNECTED_DELAY=30,
    )
    return _load_source("tuya_ble.devices", "devices.py")


class BrandsonClimateMappingTests(unittest.TestCase):
    def test_product_registration_is_exact(self):
        devices = load_devices_module()

        info = devices.get_product_info_by_ids("xbx_2b_2", "boagb65r")

        self.assertIsNotNone(info)
        self.assertEqual("Brandson Coolbox", info.name)
        self.assertIsNone(devices.get_product_info_by_ids("xbx_2b_2", "different"))

    def test_climate_mapping_is_exact(self):
        climate = load_climate_module()

        mappings = climate.get_mapping_by_device(_FakeDevice())

        self.assertEqual(1, len(mappings))
        item = mappings[0]
        self.assertEqual(101, item.hvac_switch_dp_id)
        self.assertEqual(climate.HVACMode.COOL, item.hvac_switch_mode)
        self.assertEqual(112, item.current_temperature_dp_id)
        self.assertEqual(114, item.target_temperature_dp_id)
        self.assertEqual(105, item.temperature_unit_dp_id)
        self.assertEqual(102, item.hvac_action_dp_id)
        self.assertEqual((-20.0, 20.0, 1.0), (
            item.target_temperature_min,
            item.target_temperature_max,
            item.target_temperature_step,
        ))
        self.assertEqual(
            [], climate.get_mapping_by_device(_FakeDevice(product_id="different"))
        )


class BrandsonClimateEntityTests(unittest.IsolatedAsyncioTestCase):
    def _entity(self):
        climate = load_climate_module()
        device = _FakeDevice()
        hass = _FakeHass()
        mappings = climate.get_mapping_by_device(device)
        self.assertEqual(1, len(mappings), "Brandson climate mapping is missing")
        mapping = mappings[0]
        entity = climate.TuyaBLEClimate(
            hass,
            _Coordinator(),
            device,
            types.SimpleNamespace(name="Brandson Coolbox"),
            mapping,
        )
        return climate, hass, device, entity

    async def test_fahrenheit_values_are_exposed_as_celsius(self):
        climate, _, device, entity = self._entity()
        device.datapoints.set(101, climate.TuyaBLEDataPointType.DT_BOOL, True)
        device.datapoints.set(102, climate.TuyaBLEDataPointType.DT_BOOL, True)
        device.datapoints.set(105, climate.TuyaBLEDataPointType.DT_ENUM, 1)
        device.datapoints.set(112, climate.TuyaBLEDataPointType.DT_VALUE, 68)
        device.datapoints.set(114, climate.TuyaBLEDataPointType.DT_VALUE, 7)

        entity._handle_coordinator_update()

        self.assertAlmostEqual(20.0, entity._attr_current_temperature)
        self.assertAlmostEqual(-13.8888888889, entity._attr_target_temperature)
        self.assertEqual(climate.HVACAction.COOLING, entity._attr_hvac_action)

    async def test_celsius_target_is_written_in_active_device_unit(self):
        climate, hass, device, entity = self._entity()
        device.datapoints.set(105, climate.TuyaBLEDataPointType.DT_ENUM, 1)

        await entity.async_set_temperature(temperature=-14)
        await asyncio.gather(*hass.tasks)

        self.assertEqual(7, device.datapoints[114].last_set_value)

    async def test_unit_change_waits_for_new_temperature_datapoints(self):
        climate, _, device, entity = self._entity()
        entity._attr_current_temperature = 25.0
        entity._attr_target_temperature = -14.0
        device.datapoints.set(105, climate.TuyaBLEDataPointType.DT_ENUM, 1, 20)
        device.datapoints.set(112, climate.TuyaBLEDataPointType.DT_VALUE, 25, 10)
        device.datapoints.set(114, climate.TuyaBLEDataPointType.DT_VALUE, -14, 10)

        entity._handle_coordinator_update()

        self.assertEqual(25.0, entity._attr_current_temperature)
        self.assertEqual(-14.0, entity._attr_target_temperature)

        device.datapoints.set(112, climate.TuyaBLEDataPointType.DT_VALUE, 77, 21)
        device.datapoints.set(114, climate.TuyaBLEDataPointType.DT_VALUE, 7, 21)
        entity._handle_coordinator_update()

        self.assertAlmostEqual(25.0, entity._attr_current_temperature)
        self.assertAlmostEqual(-13.8888888889, entity._attr_target_temperature)

    async def test_power_uses_boolean_dp_101(self):
        climate, hass, device, entity = self._entity()

        await entity.async_set_hvac_mode(climate.HVACMode.COOL)
        await asyncio.gather(*hass.tasks)

        self.assertIs(True, device.datapoints[101].last_set_value)


if __name__ == "__main__":
    unittest.main()
