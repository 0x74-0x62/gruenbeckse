"""Button platform for Grünbeck softliQ SE."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import GruenbeckSECoordinator
from .entity import GruenbeckSEEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SEButtonDescription(ButtonEntityDescription):
    """Button description with an async action callable."""
    action_fn: Any = None


BUTTONS: tuple[SEButtonDescription, ...] = (
    SEButtonDescription(
        key="regenerate",
        translation_key="regenerate",
        icon="mdi:refresh",
        action_fn=lambda c: c.async_regenerate(),
    ),
    SEButtonDescription(
        key="clear_regen_counter",
        translation_key="clear_regen_counter",
        icon="mdi:counter",
        action_fn=lambda c: c.async_set_parameter("pclearcntreg", True),
        entity_registry_enabled_default=False,
    ),
    SEButtonDescription(
        key="clear_water_counter",
        translation_key="clear_water_counter",
        icon="mdi:water-off",
        action_fn=lambda c: c.async_set_parameter("pclearcntwater", True),
        entity_registry_enabled_default=False,
    ),
    SEButtonDescription(
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
    coordinator: GruenbeckSECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GruenbeckSEButton(coordinator, entry, desc) for desc in BUTTONS
    )


class GruenbeckSEButton(GruenbeckSEEntity, ButtonEntity):
    """A button entity for the Grünbeck softliQ SE."""

    entity_description: SEButtonDescription

    def __init__(
        self,
        coordinator: GruenbeckSECoordinator,
        entry: ConfigEntry,
        description: SEButtonDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        try:
            await self.entity_description.action_fn(self.coordinator)
        except Exception as exc:
            _LOGGER.error("Button %s failed: %s", self.entity_description.key, exc)
            raise HomeAssistantError(
                f"Failed to trigger {self.entity_description.name or self.entity_description.key}: {exc}"
            ) from exc
