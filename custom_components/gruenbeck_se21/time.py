"""Time platform for Grünbeck softliQ SE21 — regeneration schedule times."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import GruenbeckSE21Coordinator
from .entity import GruenbeckSE21Entity

_LOGGER = logging.getLogger(__name__)

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")

_DAYS = (
    ("pregsu", "su"),
    ("pregmo", "mo"),
    ("pregdi", "di"),
    ("pregmi", "mi"),
    ("pregdo", "do"),
    ("pregfr", "fr"),
    ("pregsa", "sa"),
)


@dataclass(frozen=True)
class SE21TimeDescription(TimeEntityDescription):
    """Time description with the raw parameter key for PATCH."""
    param_key: str = ""


TIMES: tuple[SE21TimeDescription, ...] = tuple(
    SE21TimeDescription(
        key=f"param_{day_param}{slot}",
        translation_key=f"regen_time_{day_abbr}_{slot}",
        icon="mdi:clock-outline",
        param_key=f"{day_param}{slot}",
        entity_registry_enabled_default=False,
    )
    for day_param, day_abbr in _DAYS
    for slot in (1, 2, 3)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckSE21Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GruenbeckSE21Time(coordinator, entry, desc) for desc in TIMES
    )


class GruenbeckSE21Time(GruenbeckSE21Entity, TimeEntity):
    """A regeneration schedule time slot as a time entity."""

    entity_description: SE21TimeDescription

    def __init__(
        self,
        coordinator: GruenbeckSE21Coordinator,
        entry: ConfigEntry,
        description: SE21TimeDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> dt_time | None:
        raw = (self.coordinator.data or {}).get(self.entity_description.key)
        if isinstance(raw, dt_time):
            return raw
        if not raw:
            return None
        m = _TIME_RE.match(str(raw))
        if m:
            return dt_time(int(m.group(1)), int(m.group(2)))
        return None

    async def async_set_value(self, value: dt_time) -> None:
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        try:
            await self.coordinator.async_set_parameter(
                self.entity_description.param_key, time_str
            )
        except Exception as exc:
            _LOGGER.error(
                "Failed to set %s to %s: %s", self.entity_description.key, time_str, exc
            )
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name or self.entity_description.key} to {time_str}: {exc}"
            ) from exc
