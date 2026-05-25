"""Base entity for Grünbeck softliQ SE21."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GruenbeckSE21Coordinator


class GruenbeckSE21Entity(CoordinatorEntity[GruenbeckSE21Coordinator]):
    """Base entity — provides dynamic DeviceInfo incl. firmware versions."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GruenbeckSE21Coordinator,
        entry: ConfigEntry,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_{unique_suffix}"
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Grünbeck",
            model="softliQ SE21",
            sw_version=data.get("sw_version"),
            hw_version=data.get("hw_version"),
        )
