"""Button platform for Grünbeck softliQ SE21."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GruenbeckSE21Coordinator
from .entity import GruenbeckSE21Entity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SE21ButtonDescription(ButtonEntityDescription):
    """Button description with an async action callable."""
    action_fn: Any = None


BUTTONS: tuple[SE21ButtonDescription, ...] = (
    SE21ButtonDescription(
        key="regenerate",
        translation_key="regenerate",
        icon="mdi:refresh",
        action_fn=lambda c: c.async_regenerate(),
    ),
    SE21ButtonDescription(
        key="clear_regen_counter",
        translation_key="clear_regen_counter",
        icon="mdi:counter",
        action_fn=lambda c: c.async_set_parameter("pclearcntreg", True),
        entity_registry_enabled_default=False,
    ),
    SE21ButtonDescription(
        key="clear_water_counter",
        translation_key="clear_water_counter",
        icon="mdi:water-off",
        action_fn=lambda c: c.async_set_parameter("pclearcntwater", True),
        entity_registry_enabled_default=False,
    ),
    SE21ButtonDescription(
        key="clear_error_memory",
        translation_key="clear_error_memory",
        icon="mdi:alert-remove",
        action_fn=lambda c: c.async_set_parameter("pclearerrmem", True),
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
        GruenbeckSE21Button(coordinator, entry, desc) for desc in BUTTONS
    )


class GruenbeckSE21Button(GruenbeckSE21Entity, ButtonEntity):
    """A button entity for the Grünbeck softliQ SE21."""

    entity_description: SE21ButtonDescription

    def __init__(
        self,
        coordinator: GruenbeckSE21Coordinator,
        entry: ConfigEntry,
        description: SE21ButtonDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        try:
            await self.entity_description.action_fn(self.coordinator)
        except Exception as exc:
            _LOGGER.error("Button %s failed: %s", self.entity_description.key, exc)
