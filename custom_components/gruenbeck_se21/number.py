"""Number platform for Grünbeck softliQ SE — writable numeric parameters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import GruenbeckSECoordinator
from .entity import GruenbeckSEEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SENumberDescription(NumberEntityDescription):
    """Number description with the raw parameter key for PATCH."""
    param_key: str = ""
    as_string: bool = False  # True when the API expects a string value (e.g. pledbright)


NUMBERS: tuple[SENumberDescription, ...] = (
    SENumberDescription(
        key="param_pled",
        translation_key="led_mode",
        icon="mdi:led-variant-on",
        param_key="pled",
        native_min_value=0,
        native_max_value=8,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_registry_enabled_default=False,
    ),
    SENumberDescription(
        key="param_pledbright",
        translation_key="led_brightness",
        icon="mdi:brightness-6",
        param_key="pledbright",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.BOX,
        as_string=True,  # API expects string ("39", "41", …)
        entity_registry_enabled_default=False,
    ),
    SENumberDescription(
        key="param_psetsoft",
        translation_key="target_soft_water_hardness",
        icon="mdi:water-check",
        param_key="psetsoft",
        native_min_value=0,
        native_max_value=25,
        native_step=1,
        native_unit_of_measurement="°dH",
        mode=NumberMode.BOX,
        entity_registry_enabled_default=False,
    ),
    SENumberDescription(
        key="param_prawhard",
        translation_key="raw_water_hardness",
        icon="mdi:water-plus",
        param_key="prawhard",
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        native_unit_of_measurement="°dH",
        mode=NumberMode.BOX,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckSECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GruenbeckSENumber(coordinator, entry, desc) for desc in NUMBERS
    )


class GruenbeckSENumber(GruenbeckSEEntity, NumberEntity):
    """A writable numeric parameter as a number entity."""

    entity_description: SENumberDescription

    def __init__(
        self,
        coordinator: GruenbeckSECoordinator,
        entry: ConfigEntry,
        description: SENumberDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        val = (self.coordinator.data or {}).get(self.entity_description.key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        int_val = int(value)
        api_val = str(int_val) if self.entity_description.as_string else int_val
        try:
            await self.coordinator.async_set_parameter(
                self.entity_description.param_key, api_val
            )
        except Exception as exc:
            _LOGGER.error(
                "Failed to set %s to %r: %s", self.entity_description.key, api_val, exc
            )
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name or self.entity_description.key} to {api_val}: {exc}"
            ) from exc
