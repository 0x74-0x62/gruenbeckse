"""Switch platform for Grünbeck softliQ SE21 — writable boolean parameters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GruenbeckSE21Coordinator
from .entity import GruenbeckSE21Entity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SE21SwitchDescription(SwitchEntityDescription):
    """Switch description with the raw parameter key for PATCH."""
    param_key: str = ""


SWITCHES: tuple[SE21SwitchDescription, ...] = (
    SE21SwitchDescription(
        key="param_pregmode",
        translation_key="regeneration_mode",
        icon="mdi:refresh-auto",
        param_key="pregmode",
        entity_registry_enabled_default=False,
    ),
    SE21SwitchDescription(
        key="param_pbuzzer",
        translation_key="buzzer",
        icon="mdi:bell",
        param_key="pbuzzer",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckSE21Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GruenbeckSE21Switch(coordinator, entry, desc) for desc in SWITCHES
    )


class GruenbeckSE21Switch(GruenbeckSE21Entity, SwitchEntity):
    """A writable boolean parameter as a switch entity."""

    entity_description: SE21SwitchDescription

    def __init__(
        self,
        coordinator: GruenbeckSE21Coordinator,
        entry: ConfigEntry,
        description: SE21SwitchDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        val = (self.coordinator.data or {}).get(self.entity_description.key)
        return bool(val) if val is not None else None

    async def async_turn_on(self, **kwargs: object) -> None:
        try:
            await self.coordinator.async_set_parameter(
                self.entity_description.param_key, True
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn on %s: %s", self.entity_description.key, exc)

    async def async_turn_off(self, **kwargs: object) -> None:
        try:
            await self.coordinator.async_set_parameter(
                self.entity_description.param_key, False
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn off %s: %s", self.entity_description.key, exc)
