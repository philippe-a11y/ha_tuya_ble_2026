"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass

import logging
from typing import Callable

from homeassistant.components.climate import (
    ClimateEntityDescription,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    PRESET_AWAY,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .brandson_coolbox import (
    CATEGORY as BRANDSON_CATEGORY,
    DP_COMPRESSOR,
    DP_CURRENT_TEMPERATURE,
    DP_POWER,
    DP_TARGET_TEMPERATURE,
    DP_TEMPERATURE_UNIT,
    PRODUCT_ID as BRANDSON_PRODUCT_ID,
    TARGET_MAX_C,
    TARGET_MIN_C,
    TARGET_STEP_C,
    UNIT_CELSIUS,
    UNIT_FAHRENHEIT,
    celsius_to_device_temperature,
    device_temperature_to_celsius,
)
from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPoint, TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLEClimateMapping:
    description: ClimateEntityDescription

    hvac_mode_dp_id: int = 0
    hvac_modes: list[str] | None = None

    hvac_switch_dp_id: int = 0
    hvac_switch_mode: HVACMode | None = None

    preset_mode_dp_ids: dict[str, int] | None = None

    temperature_unit: str = UnitOfTemperature.CELSIUS
    current_temperature_dp_id: int = 0
    current_temperature_coefficient: float = 1.0
    target_temperature_dp_id: int = 0
    target_temperature_coefficient: float = 1.0
    target_temperature_max: float = 30.0
    target_temperature_min: float = 5
    target_temperature_step: float = 1.0
    temperature_unit_dp_id: int = 0

    hvac_action_dp_id: int = 0
    hvac_action_active: HVACAction | None = None

    current_humidity_dp_id: int = 0
    current_humidity_coefficient: float = 1.0
    target_humidity_dp_id: int = 0
    target_humidity_coefficient: float = 1.0
    target_humidity_max: float = 100.0
    target_humidity_min: float = 0.0


@dataclass
class TuyaBLECategoryClimateMapping:
    products: dict[str, list[TuyaBLEClimateMapping]] | None = None
    mapping: list[TuyaBLEClimateMapping] | None = None


mapping: dict[str, TuyaBLECategoryClimateMapping] = {
    BRANDSON_CATEGORY: TuyaBLECategoryClimateMapping(
        products={
            BRANDSON_PRODUCT_ID: [
                TuyaBLEClimateMapping(
                    description=ClimateEntityDescription(
                        key="coolbox",
                    ),
                    hvac_switch_dp_id=DP_POWER,
                    hvac_switch_mode=HVACMode.COOL,
                    hvac_modes=[HVACMode.OFF, HVACMode.COOL],
                    hvac_action_dp_id=DP_COMPRESSOR,
                    hvac_action_active=HVACAction.COOLING,
                    temperature_unit=UnitOfTemperature.CELSIUS,
                    temperature_unit_dp_id=DP_TEMPERATURE_UNIT,
                    current_temperature_dp_id=DP_CURRENT_TEMPERATURE,
                    target_temperature_dp_id=DP_TARGET_TEMPERATURE,
                    target_temperature_min=TARGET_MIN_C,
                    target_temperature_max=TARGET_MAX_C,
                    target_temperature_step=TARGET_STEP_C,
                ),
            ],
        },
    ),
    "wk": TuyaBLECategoryClimateMapping(
        products={
            **dict.fromkeys(
                [
                "drlajpqc", 
                "nhj2j7su",
                ],  # Thermostatic Radiator Valve
                [
                # Thermostatic Radiator Valve
                # - [x] 8   - Window
                # - [x] 10  - Antifreeze
                # - [x] 27  - Calibration
                # - [x] 40  - Lock
                # - [x] 101 - Switch
                # - [x] 102 - Current
                # - [x] 103 - Target
                # - [ ] 104 - Heating time
                # - [x] 105 - Battery power alarm
                # - [x] 106 - Away
                # - [x] 107 - Programming mode
                # - [x] 108 - Programming switch
                # - [ ] 109 - Programming data (deprecated - do not delete)
                # - [ ] 110 - Historical data protocol (Day-Target temperature)
                # - [ ] 111 - System Time Synchronization
                # - [ ] 112 - Historical data (Week-Target temperature)
                # - [ ] 113 - Historical data (Month-Target temperature)
                # - [ ] 114 - Historical data (Year-Target temperature)
                # - [ ] 115 - Historical data (Day-Current temperature)
                # - [ ] 116 - Historical data (Week-Current temperature)
                # - [ ] 117 - Historical data (Month-Current temperature)
                # - [ ] 118 - Historical data (Year-Current temperature)
                # - [ ] 119 - Historical data (Day-motor opening degree)
                # - [ ] 120 - Historical data (Week-motor opening degree)
                # - [ ] 121 - Historical data (Month-motor opening degree)
                # - [ ] 122 - Historical data (Year-motor opening degree)
                # - [ ] 123 - Programming data (Monday)
                # - [ ] 124 - Programming data (Tuseday)
                # - [ ] 125 - Programming data (Wednesday)
                # - [ ] 126 - Programming data (Thursday)
                # - [ ] 127 - Programming data (Friday)
                # - [ ] 128 - Programming data (Saturday)
                # - [ ] 129 - Programming data (Sunday)
                # - [x] 130 - Water scale
                TuyaBLEClimateMapping(
                    description=ClimateEntityDescription(
                        key="thermostatic_radiator_valve",
                    ),
                    hvac_switch_dp_id=101,
                    hvac_switch_mode=HVACMode.HEAT,
                    hvac_modes=[HVACMode.OFF, HVACMode.HEAT],
                    preset_mode_dp_ids={PRESET_AWAY: 106, PRESET_NONE: 106},
                    current_temperature_dp_id=102,
                    current_temperature_coefficient=10.0,
                    target_temperature_coefficient=10.0,
                    target_temperature_step=0.5,
                    target_temperature_dp_id=103,
                    target_temperature_min=5.0,
                    target_temperature_max=30.0,
                    ),
                ],
            ),
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategoryClimateMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLEClimate(TuyaBLEEntity, ClimateEntity):
    """Representation of a Tuya BLE Climate."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEClimateMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_preset_mode = PRESET_NONE
        self._attr_hvac_action = HVACAction.HEATING

        if mapping.hvac_mode_dp_id and mapping.hvac_modes:
            self._attr_hvac_modes = mapping.hvac_modes
        elif mapping.hvac_switch_dp_id and mapping.hvac_switch_mode:
            self._attr_hvac_modes = [HVACMode.OFF, mapping.hvac_switch_mode]

        if mapping.preset_mode_dp_ids:
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = list(mapping.preset_mode_dp_ids.keys())

        if mapping.target_temperature_dp_id != 0:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_temperature_unit = mapping.temperature_unit
            self._attr_max_temp = mapping.target_temperature_max
            self._attr_min_temp = mapping.target_temperature_min
            self._attr_target_temperature_step = mapping.target_temperature_step

        if mapping.target_humidity_dp_id != 0:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_HUMIDITY
            self._attr_max_humidity = mapping.target_humidity_max
            self._attr_min_humidity = mapping.target_humidity_min

    def _temperature_unit_value(self) -> int:
        """Return the device display unit, defaulting safely to Celsius."""
        if self._mapping.temperature_unit_dp_id:
            datapoint = self._device.datapoints[
                self._mapping.temperature_unit_dp_id
            ]
            if datapoint and datapoint.value == UNIT_FAHRENHEIT:
                return UNIT_FAHRENHEIT
        return UNIT_CELSIUS

    def _temperature_from_device(self, value: float, coefficient: float) -> float:
        """Scale a raw value and convert a unit-aware mapping to Celsius."""
        result = value / coefficient
        if self._mapping.temperature_unit_dp_id:
            return device_temperature_to_celsius(
                result, self._temperature_unit_value()
            )
        return result

    def _temperature_datapoint_is_current(self, datapoint: TuyaBLEDataPoint) -> bool:
        """Wait for temperatures reported at or after a display-unit change."""
        if not self._mapping.temperature_unit_dp_id:
            return True
        unit_dp = self._device.datapoints[self._mapping.temperature_unit_dp_id]
        if not unit_dp:
            return True
        return getattr(datapoint, "timestamp", 0) >= getattr(unit_dp, "timestamp", 0)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if self._mapping.current_temperature_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.current_temperature_dp_id]
            if datapoint and self._temperature_datapoint_is_current(datapoint):
                self._attr_current_temperature = self._temperature_from_device(
                    datapoint.value,
                    self._mapping.current_temperature_coefficient,
                )

        if self._mapping.target_temperature_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.target_temperature_dp_id]
            if datapoint and self._temperature_datapoint_is_current(datapoint):
                self._attr_target_temperature = self._temperature_from_device(
                    datapoint.value,
                    self._mapping.target_temperature_coefficient,
                )

        if self._mapping.current_humidity_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.current_humidity_dp_id]
            if datapoint:
                self._attr_current_humidity = (
                    datapoint.value / self._mapping.current_humidity_coefficient
                )

        if self._mapping.target_humidity_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.target_humidity_dp_id]
            if datapoint:
                self._attr_target_humidity = (
                    datapoint.value / self._mapping.target_humidity_coefficient
                )

        if self._mapping.hvac_mode_dp_id != 0 and self._mapping.hvac_modes:
            datapoint = self._device.datapoints[self._mapping.hvac_mode_dp_id]
            if datapoint:
                self._attr_hvac_mode = (
                    self._mapping.hvac_modes[datapoint.value]
                    if datapoint.value < len(self._mapping.hvac_modes)
                    else None
                )
        elif self._mapping.hvac_switch_dp_id != 0 and self._mapping.hvac_switch_mode:
            datapoint = self._device.datapoints[self._mapping.hvac_switch_dp_id]
            if datapoint:
                self._attr_hvac_mode = (
                    self._mapping.hvac_switch_mode if datapoint.value else HVACMode.OFF
                )

        if self._mapping.preset_mode_dp_ids:
            current_preset_mode = PRESET_NONE
            for preset_mode, dp_id in self._mapping.preset_mode_dp_ids.items():
                datapoint = self._device.datapoints[dp_id]
                if datapoint and datapoint.value:
                    current_preset_mode = preset_mode
                    break
            self._attr_preset_mode = current_preset_mode

        if self._mapping.hvac_action_dp_id and self._mapping.hvac_action_active:
            action_dp = self._device.datapoints[self._mapping.hvac_action_dp_id]
            if self._attr_hvac_mode == HVACMode.OFF:
                self._attr_hvac_action = HVACAction.OFF
            elif action_dp and bool(action_dp.value):
                self._attr_hvac_action = self._mapping.hvac_action_active
            else:
                self._attr_hvac_action = HVACAction.IDLE
        else:
            try:
                if (
                    self._attr_preset_mode == PRESET_AWAY
                    or self._attr_hvac_mode == HVACMode.OFF
                    or self._attr_target_temperature <= self._attr_current_temperature
                ):
                    self._attr_hvac_action = HVACAction.IDLE
                else:
                    self._attr_hvac_action = HVACAction.HEATING
            except (AttributeError, TypeError):
                pass

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if self._mapping.target_temperature_dp_id != 0:
            value = kwargs["temperature"]
            if self._mapping.temperature_unit_dp_id:
                value = celsius_to_device_temperature(
                    value, self._temperature_unit_value()
                )
            int_value = int(round(
                value * self._mapping.target_temperature_coefficient
            ))
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.target_temperature_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if self._mapping.target_humidity_dp_id != 0:
            int_value = int(humidity * self._mapping.target_humidity_coefficient)
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.target_humidity_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if (
            self._mapping.hvac_mode_dp_id != 0
            and self._mapping.hvac_modes
            and hvac_mode in self._mapping.hvac_modes
        ):
            int_value = self._mapping.hvac_modes.index(hvac_mode)
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.target_humidity_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))
        elif self._mapping.hvac_switch_dp_id != 0 and self._mapping.hvac_switch_mode:
            bool_value = hvac_mode == self._mapping.hvac_switch_mode
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.hvac_switch_dp_id,
                TuyaBLEDataPointType.DT_BOOL,
                bool_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(bool_value))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if self._mapping.preset_mode_dp_ids:
            datapoint: TuyaBLEDataPoint | None = None
            bool_value = False

            keys = [x for x in self._mapping.preset_mode_dp_ids.keys()]
            values = [
                x for x in self._mapping.preset_mode_dp_ids.values()
            ]  # Get all DP IDs
            # TRVs with only Away and None modes can be set with a single datapoint and use a single DP ID
            if all(values[0] == elem for elem in values) and keys[0] == PRESET_AWAY:
                for dp_id in values:
                    bool_value = preset_mode == PRESET_AWAY
                    datapoint = self._device.datapoints.get_or_create(
                        dp_id,
                        TuyaBLEDataPointType.DT_BOOL,
                        bool_value,
                    )
                    break
            else:
                if self._mapping.preset_mode_dp_ids:
                    for (
                        dp_preset_mode,
                        dp_id,
                    ) in self._mapping.preset_mode_dp_ids.items():
                        bool_value = dp_preset_mode == preset_mode
                        datapoint = self._device.datapoints.get_or_create(
                            dp_id,
                            TuyaBLEDataPointType.DT_BOOL,
                            bool_value,
                        )
            if datapoint:
                self._hass.create_task(datapoint.set_value(bool_value))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLEClimate] = []
    for mapping in mappings:
        entities.append(
            TuyaBLEClimate(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mapping,
            )
        )
    async_add_entities(entities)
