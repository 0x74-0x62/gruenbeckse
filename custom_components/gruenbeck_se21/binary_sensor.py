"""Binary sensors for Grünbeck softliQ SE21."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GruenbeckSE21Coordinator
from .entity import GruenbeckSE21Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckSE21Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GruenbeckSE21ErrorSensor(coordinator, entry),
        GruenbeckSE21LowSaltSensor(coordinator, entry),
    ])


class GruenbeckSE21ErrorSensor(GruenbeckSE21Entity, BinarySensorEntity):
    """Binary sensor: device error / Gerätestörung."""

    _attr_translation_key = "has_error"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: GruenbeckSE21Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "has_error")

    @property
    def is_on(self) -> bool | None:
        return (self.coordinator.data or {}).get("has_error")

    @property
    def extra_state_attributes(self) -> dict | None:
        active = (self.coordinator.data or {}).get("active_errors") or []
        if not active:
            return None
        return {"error_count": len(active), "errors": active}


class GruenbeckSE21LowSaltSensor(GruenbeckSE21Entity, BinarySensorEntity):
    """Binary sensor: salt low warning (errorCode 26 — Salzvorrat gering)."""

    _attr_translation_key = "low_salt"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator: GruenbeckSE21Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "low_salt")

    @property
    def is_on(self) -> bool | None:
        val = (self.coordinator.data or {}).get("low_salt")
        return bool(val) if val is not None else None
