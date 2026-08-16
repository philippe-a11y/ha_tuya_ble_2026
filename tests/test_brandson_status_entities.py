from __future__ import annotations

import asyncio
from dataclasses import dataclass
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
    def __init__(self, key: str = "", **kwargs):
        self.key = key
        self.translation_key = kwargs.pop("translation_key", None)
        self.options = kwargs.pop("options", None)
        for name, value in kwargs.items():
            setattr(self, name, value)


class _BaseEntity:
    def __init__(self, hass, coordinator, device, product, description):
        self._hass = hass
        self._device = device
        self._product = product
        self.entity_description = description

    def async_write_ha_state(self):
        return None

    @property
    def available(self):
        return True


class _FakeDataPoint:
    def __init__(self, dp_type, value):
        self.type = dp_type
        self.value = value
        self.last_set_value = None

    async def set_value(self, value):
        self.last_set_value = value
        self.value = value


class _FakeDataPoints:
    def __init__(self):
        self._items = {}

    def __getitem__(self, dp_id):
        return self._items.get(dp_id)

    def set(self, dp_id, dp_type, value):
        self._items[dp_id] = _FakeDataPoint(dp_type, value)

    def has_id(self, dp_id, dp_type=None):
        return dp_id in self._items

    def get_or_create(self, dp_id, dp_type, value):
        item = self._items.get(dp_id)
        if item is None:
            item = _FakeDataPoint(dp_type, value)
            self._items[dp_id] = item
        return item


class _FakeDevice:
    def __init__(self, category="xbx_2b_2", product_id="boagb65r"):
        self.category = category
        self.product_id = product_id
        self.datapoints = _FakeDataPoints()
        self.rssi = -60


class _EntityCategory:
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


class _DataPointType:
    DT_BOOL = "bool"
    DT_VALUE = "value"
    DT_ENUM = "enum"
    DT_BITMAP = "bitmap"


def _clear_modules():
    for name in list(sys.modules):
        if name == "tuya_ble" or name.startswith("tuya_ble."):
            del sys.modules[name]


def _load_source(name: str, filename: str):
    path = ROOT / "tuya_ble" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _install_common():
    _clear_modules()
    package = _module("tuya_ble")
    package.__path__ = [str(ROOT / "tuya_ble")]
    _load_source("tuya_ble.brandson_coolbox", "brandson_coolbox.py")

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    components = _module("homeassistant.components")
    components.__path__ = []
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module("homeassistant.core", HomeAssistant=object, callback=lambda function: function)
    _module("homeassistant.helpers.entity", EntityCategory=_EntityCategory)
    _module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    _module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=object)
    _module(
        "tuya_ble.devices",
        TuyaBLEData=object,
        TuyaBLEEntity=_BaseEntity,
        TuyaBLEProductInfo=object,
    )
    _module(
        "tuya_ble.tuya_ble",
        TuyaBLEDataPointType=_DataPointType,
        TuyaBLEDevice=_FakeDevice,
    )


def load_sensor_module():
    _install_common()

    class SensorEntity:
        pass

    class SensorDeviceClass:
        BATTERY = "battery"
        CO = "carbon_monoxide"
        CO2 = "co2"
        DURATION = "duration"
        ENUM = "enum"
        HUMIDITY = "humidity"
        MOISTURE = "moisture"
        SIGNAL_STRENGTH = "signal_strength"
        TEMPERATURE = "temperature"
        VOLTAGE = "voltage"
        WATER = "water"

    class SensorStateClass:
        MEASUREMENT = "measurement"

    _module(
        "homeassistant.components.sensor",
        SensorDeviceClass=SensorDeviceClass,
        SensorEntity=SensorEntity,
        SensorEntityDescription=_Description,
        SensorStateClass=SensorStateClass,
    )

    class UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"

    class UnitOfTime:
        MINUTES = "min"

    class UnitOfElectricPotential:
        VOLT = "V"

    _module(
        "homeassistant.const",
        CONCENTRATION_PARTS_PER_MILLION="ppm",
        PERCENTAGE="%",
        SIGNAL_STRENGTH_DECIBELS_MILLIWATT="dBm",
        TEMP_CELSIUS="°C",
        VOLUME_MILLILITERS="mL",
        UnitOfElectricPotential=UnitOfElectricPotential,
        UnitOfTemperature=UnitOfTemperature,
        UnitOfTime=UnitOfTime,
    )
    _module(
        "tuya_ble.const",
        BATTERY_STATE_HIGH="high",
        BATTERY_STATE_LOW="low",
        BATTERY_STATE_NORMAL="normal",
        BATTERY_CHARGED="charged",
        BATTERY_CHARGING="charging",
        BATTERY_NOT_CHARGING="not_charging",
        CO2_LEVEL_ALARM="alarm",
        CO2_LEVEL_NORMAL="normal",
        DOMAIN="tuya_ble",
    )
    return _load_source("tuya_ble.sensor", "sensor.py")


def load_binary_sensor_module():
    _install_common()

    class BinarySensorEntity:
        pass

    class BinarySensorDeviceClass:
        BATTERY = "battery"
        LOCK = "lock"
        PROBLEM = "problem"
        RUNNING = "running"

    _module(
        "homeassistant.components.binary_sensor",
        BinarySensorDeviceClass=BinarySensorDeviceClass,
        BinarySensorEntity=BinarySensorEntity,
        BinarySensorEntityDescription=_Description,
    )
    _module("tuya_ble.const", DOMAIN="tuya_ble")
    return _load_source("tuya_ble.binary_sensor", "binary_sensor.py")


def load_select_module():
    _install_common()

    @dataclass
    class SelectEntityDescription:
        key: str = ""
        icon: str | None = None
        entity_category: str | None = None
        options: list[str] | None = None
        entity_registry_enabled_default: bool = True

    class SelectEntity:
        pass

    _module(
        "homeassistant.components.select",
        SelectEntityDescription=SelectEntityDescription,
        SelectEntity=SelectEntity,
    )

    class UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"

    _module("homeassistant.const", UnitOfTemperature=UnitOfTemperature)
    _module(
        "tuya_ble.const",
        DOMAIN="tuya_ble",
        FINGERBOT_MODE_PROGRAM="program",
        FINGERBOT_MODE_PUSH="push",
        FINGERBOT_MODE_SWITCH="switch",
    )
    return _load_source("tuya_ble.select", "select.py")


class _FakeHass:
    def __init__(self):
        self.tasks = []

    def create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


class BrandsonSensorTests(unittest.TestCase):
    def test_voltage_and_battery_values(self):
        sensor = load_sensor_module()
        device = _FakeDevice()
        mappings = sensor.get_mapping_by_device(device)

        self.assertEqual(
            [(122, "input_voltage"), (123, "battery")],
            [(item.dp_id, item.description.key) for item in mappings],
        )
        device.datapoints.set(122, _DataPointType.DT_VALUE, 132)
        device.datapoints.set(123, _DataPointType.DT_VALUE, 88)
        voltage = sensor.TuyaBLESensor(None, None, device, None, mappings[0])
        battery = sensor.TuyaBLESensor(None, None, device, None, mappings[1])

        voltage._handle_coordinator_update()
        battery._handle_coordinator_update()

        self.assertEqual(13.2, voltage._attr_native_value)
        self.assertEqual(88, battery._attr_native_value)
        self.assertEqual("V", mappings[0].description.native_unit_of_measurement)
        self.assertEqual("%", mappings[1].description.native_unit_of_measurement)

    def test_status_mappings_are_exact_to_product(self):
        sensor = load_sensor_module()

        self.assertEqual(
            [], sensor.get_mapping_by_device(_FakeDevice(product_id="different"))
        )


class BrandsonBinarySensorTests(unittest.TestCase):
    def test_compressor_and_fault_bitmap(self):
        binary_sensor = load_binary_sensor_module()
        device = _FakeDevice()
        mappings = binary_sensor.get_mapping_by_device(device)

        self.assertEqual(
            [(102, "compressor_running"), (106, "fault")],
            [(item.dp_id, item.description.key) for item in mappings],
        )
        device.datapoints.set(102, _DataPointType.DT_BOOL, True)
        device.datapoints.set(106, _DataPointType.DT_BITMAP, b"\x00")
        compressor = binary_sensor.TuyaBLEBinarySensor(
            None, None, device, None, mappings[0]
        )
        fault = binary_sensor.TuyaBLEBinarySensor(None, None, device, None, mappings[1])

        compressor._handle_coordinator_update()
        fault._handle_coordinator_update()

        self.assertIs(True, compressor._attr_is_on)
        self.assertIs(False, fault._attr_is_on)

        device.datapoints.set(106, _DataPointType.DT_BITMAP, b"\x00\x04")
        fault._handle_coordinator_update()
        self.assertIs(True, fault._attr_is_on)

    def test_binary_mappings_are_exact_to_product(self):
        binary_sensor = load_binary_sensor_module()

        self.assertEqual(
            [],
            binary_sensor.get_mapping_by_device(
                _FakeDevice(product_id="different")
            ),
        )


class BrandsonSelectTests(unittest.IsolatedAsyncioTestCase):
    async def test_options_write_verified_enum_indices(self):
        select = load_select_module()
        device = _FakeDevice()
        hass = _FakeHass()
        mappings = select.get_mapping_by_device(device)

        self.assertEqual(
            [
                (103, "operating_mode", ["max", "eco"]),
                (104, "battery_protection", ["low", "medium", "high"]),
                (105, "temperature_unit", ["°C", "°F"]),
            ],
            [
                (item.dp_id, item.description.key, item.description.options)
                for item in mappings
            ],
        )
        entities = [
            select.TuyaBLESelect(hass, None, device, None, item)
            for item in mappings
        ]

        entities[0].select_option("eco")
        entities[1].select_option("high")
        entities[2].select_option("°F")
        await asyncio.gather(*hass.tasks)

        self.assertEqual(1, device.datapoints[103].last_set_value)
        self.assertEqual(2, device.datapoints[104].last_set_value)
        self.assertEqual(1, device.datapoints[105].last_set_value)
        self.assertTrue(
            all(item.dp_type == _DataPointType.DT_ENUM for item in mappings)
        )

    async def test_select_mappings_are_exact_and_exclude_dp_140(self):
        select = load_select_module()

        mappings = select.get_mapping_by_device(_FakeDevice())

        self.assertNotIn(140, {item.dp_id for item in mappings})
        self.assertEqual(
            [], select.get_mapping_by_device(_FakeDevice(product_id="different"))
        )


if __name__ == "__main__":
    unittest.main()
