"""Sensors for Grünbeck softliQ SE."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import homeassistant.util.dt as dt_util

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfVolume, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GruenbeckSECoordinator
from .entity import GruenbeckSEEntity


@dataclass(frozen=True)
class SESensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with an optional value transform."""
    value_fn: Any = None


def _clean_temperature(val: Any) -> float | None:
    """Clean temperature value and discard negative sentinel values."""
    try:
        v = float(val)
        return None if v < 0 else v
    except (TypeError, ValueError):
        return None


def _parse_timestamp(val: Any) -> datetime | None:
    """Parse ISO timestamp and make it timezone-aware."""
    if not val:
        return None
    dt = dt_util.parse_datetime(str(val))
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)


_MODE_MAP = {
    1: "Eco",
    2: "Comfort",
    3: "Power",
    4: "Individual",
}


SENSORS: tuple[SESensorDescription, ...] = (
    # ── Measurements from /update ──────────────────────────────────────
    SESensorDescription(
        key="soft_water_quantity",
        translation_key="soft_water_quantity",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    SESensorDescription(
        key="regeneration_counter",
        translation_key="regeneration_counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
    ),
    SESensorDescription(
        key="current_flow_rate",
        translation_key="current_flow_rate",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SESensorDescription(
        key="current_flow_rate_2",
        translation_key="current_flow_rate_2",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,  # SE18/SE21 single chamber, always 0
    ),
    SESensorDescription(
        key="blending_flow_rate",
        translation_key="blending_flow_rate",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    SESensorDescription(
        key="remaining_capacity_volume",
        translation_key="remaining_capacity_volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SESensorDescription(
        key="remaining_capacity_volume_2",
        translation_key="remaining_capacity_volume_2",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,  # SE18/SE21 single chamber
    ),
    SESensorDescription(
        key="remaining_capacity_percentage",
        translation_key="remaining_capacity_percentage",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
    ),
    SESensorDescription(
        key="remaining_capacity_percentage_2",
        translation_key="remaining_capacity_percentage_2",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
        entity_registry_enabled_default=False,  # SE18/SE21 single chamber
    ),
    SESensorDescription(
        key="salt_range",
        translation_key="salt_range",
        icon="mdi:shaker-outline",
        value_fn=lambda v: "low" if v else "ok" if v is not None else None,
    ),
    SESensorDescription(
        key="salt_consumption",
        translation_key="salt_consumption",
        native_unit_of_measurement="kg",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:shaker",
        suggested_display_precision=1,
    ),
    SESensorDescription(
        key="raw_water_hardness_fh",
        translation_key="raw_water_hardness_fh",
        native_unit_of_measurement="°fH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water",
    ),
    SESensorDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,  # SE18/SE21 lack physical sensor, reports negative sentinel
        value_fn=_clean_temperature,
    ),
    SESensorDescription(
        key="make_up_water_volume",
        translation_key="make_up_water_volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-plus",
        suggested_display_precision=0,
    ),
    SESensorDescription(
        key="regeneration_step",
        translation_key="regeneration_step",
        icon="mdi:refresh",
    ),
    SESensorDescription(
        key="regeneration_step_2",
        translation_key="regeneration_step_2",
        icon="mdi:refresh",
        entity_registry_enabled_default=False,  # SE18/SE21 single chamber
    ),
    SESensorDescription(
        key="regeneration_percentage_2",
        translation_key="regeneration_percentage_2",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:refresh",
        entity_registry_enabled_default=False,  # SE18/SE21 single chamber
    ),
    SESensorDescription(
        key="regeneration_flow_rate_2",
        translation_key="regeneration_flow_rate_2",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,  # SE18/SE21 single chamber
    ),
    SESensorDescription(
        key="regeneration_trigger",
        translation_key="regeneration_trigger",
        icon="mdi:refresh-auto",
        entity_registry_enabled_default=False,
    ),
    SESensorDescription(
        key="capacity_figure",
        translation_key="capacity_figure",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        suggested_display_precision=1,
    ),
    SESensorDescription(
        key="remaining_amount_of_water",
        translation_key="remaining_amount_of_water",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water",
        suggested_display_precision=0,
        entity_registry_enabled_default=False,  # SE18/SE21 no storage tank, always 0
    ),
    # ── Device info from GET /devices/{id} ────────────────────────────
    SESensorDescription(
        key="device_status",
        translation_key="device_status",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    SESensorDescription(
        key="installed_on",
        translation_key="installed_on",
        icon="mdi:calendar",
        entity_registry_enabled_default=False,
    ),
    SESensorDescription(
        key="active_error_message",
        translation_key="active_error_message",
        icon="mdi:alert-circle-outline",
    ),
    SESensorDescription(
        key="active_error_code",
        translation_key="active_error_code",
        icon="mdi:alert-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SESensorDescription(
        key="next_regen_calc",
        translation_key="next_regen_calc",
        icon="mdi:clock-outline",
    ),
    SESensorDescription(
        key="planned_next_regeneration",
        translation_key="planned_next_regeneration",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        value_fn=_parse_timestamp,
    ),
    SESensorDescription(
        key="param_pmode",
        translation_key="operation_mode",
        icon="mdi:cog",
        value_fn=lambda v: _MODE_MAP.get(v, f"Unknown ({v})") if v is not None else None,
    ),
    SESensorDescription(
        key="param_psetsoft",
        translation_key="target_soft_water_hardness",
        native_unit_of_measurement="°dH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-check",
    ),
    SESensorDescription(
        key="param_prawhard",
        translation_key="raw_water_hardness",
        native_unit_of_measurement="°dH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-plus",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckSECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GruenbeckSESensor(coordinator, entry, desc) for desc in SENSORS
    )


class GruenbeckSESensor(GruenbeckSEEntity, SensorEntity):
    """A sensor entity for the Grünbeck softliQ SE."""

    entity_description: SESensorDescription

    def __init__(
        self,
        coordinator: GruenbeckSECoordinator,
        entry: ConfigEntry,
        description: SESensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        raw = (self.coordinator.data or {}).get(self.entity_description.key)
        if raw is None:
            return None
        fn = self.entity_description.value_fn
        return fn(raw) if fn else raw
