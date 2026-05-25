"""Switch platform for Grünbeck softliQ SE — writable boolean parameters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import GruenbeckSECoordinator
from .entity import GruenbeckSEEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SESwitchDescription(SwitchEntityDescription):
    """Switch description with the raw parameter key for PATCH."""
    param_key: str = ""


SWITCHES: tuple[SESwitchDescription, ...] = (
    SESwitchDescription(
        key="param_pregmode",
        translation_key="regeneration_mode",
        icon="mdi:refresh-auto",
        param_key="pregmode",
        entity_registry_enabled_default=False,
    ),
    SESwitchDescription(
        key="param_pbuzzer",
        translation_key="buzzer",
        icon="mdi:bell",
        param_key="pbuzzer",
        entity_registry_enabled_default=False,
    ),
)


@dataclass(frozen=True)
class SELedSwitchDescription(SwitchEntityDescription):
    """Switch description for a single LED bit derived from the pled bitmask."""
    data_key: str = ""          # coordinator data key (param_led_*)
    is_dauerhaft: bool = False  # True only for the "Dauerhaft" bit


LED_SWITCHES: tuple[SELedSwitchDescription, ...] = (
    SELedSwitchDescription(
        key="led_stoerung",
        translation_key="led_stoerung",
        icon="mdi:alert-circle",
        data_key="param_led_stoerung",
        entity_registry_enabled_default=False,
    ),
    SELedSwitchDescription(
        key="led_meldung",
        translation_key="led_meldung",
        icon="mdi:message-badge",
        data_key="param_led_meldung",
        entity_registry_enabled_default=False,
    ),
    SELedSwitchDescription(
        key="led_durchfluss",
        translation_key="led_durchfluss",
        icon="mdi:waves",
        data_key="param_led_durchfluss",
        entity_registry_enabled_default=False,
    ),
    SELedSwitchDescription(
        key="led_dauerhaft",
        translation_key="led_dauerhaft",
        icon="mdi:led-on",
        data_key="param_led_dauerhaft",
        is_dauerhaft=True,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckSECoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [
        GruenbeckSESwitch(coordinator, entry, desc) for desc in SWITCHES
    ]
    entities += [
        GruenbeckSELedSwitch(coordinator, entry, desc) for desc in LED_SWITCHES
    ]
    async_add_entities(entities)


class GruenbeckSESwitch(GruenbeckSEEntity, SwitchEntity):
    """A writable boolean parameter as a switch entity."""

    entity_description: SESwitchDescription

    def __init__(
        self,
        coordinator: GruenbeckSECoordinator,
        entry: ConfigEntry,
        description: SESwitchDescription,
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
            raise HomeAssistantError(
                f"Failed to turn on {self.entity_description.name or self.entity_description.key}: {exc}"
            ) from exc

    async def async_turn_off(self, **kwargs: object) -> None:
        try:
            await self.coordinator.async_set_parameter(
                self.entity_description.param_key, False
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn off %s: %s", self.entity_description.key, exc)
            raise HomeAssistantError(
                f"Failed to turn off {self.entity_description.name or self.entity_description.key}: {exc}"
            ) from exc


class GruenbeckSELedSwitch(GruenbeckSEEntity, SwitchEntity):
    """One of the four LED mode bits, derived from and writing back to pled."""

    entity_description: SELedSwitchDescription

    def __init__(
        self,
        coordinator: GruenbeckSECoordinator,
        entry: ConfigEntry,
        description: SELedSwitchDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        val = (self.coordinator.data or {}).get(self.entity_description.data_key)
        return bool(val) if val is not None else None

    def _compute_pled(self, overrides: dict[str, bool]) -> int:
        """Calculate the pled integer from current state + one override.

        Encoding:
          pled=0  → all LEDs off
          pled=1  → Dauerhaft (exclusive, all others off)
          pled=2…8 → n = pled-1, bit0=Störung, bit1=Meldung, bit2=Durchfluss
        """
        data = self.coordinator.data or {}

        def _get(key: str) -> bool:
            return bool(overrides.get(key, data.get(key, False)))

        dauerhaft  = _get("param_led_dauerhaft")
        stoerung   = _get("param_led_stoerung")
        meldung    = _get("param_led_meldung")
        durchfluss = _get("param_led_durchfluss")

        if dauerhaft:
            return 1
        n = (int(stoerung) * 1) + (int(meldung) * 2) + (int(durchfluss) * 4)
        return 0 if n == 0 else n + 1

    async def _set_led(self, new_state: bool) -> None:
        """Build overrides respecting Dauerhaft exclusivity, then PATCH pled."""
        data_key = self.entity_description.data_key
        overrides: dict[str, bool] = {data_key: new_state}

        if self.entity_description.is_dauerhaft and new_state:
            # Turning Dauerhaft ON → clear the three bit-based LEDs
            overrides["param_led_stoerung"]   = False
            overrides["param_led_meldung"]    = False
            overrides["param_led_durchfluss"] = False
        elif not self.entity_description.is_dauerhaft and new_state:
            # Turning a bit-LED ON → clear Dauerhaft
            overrides["param_led_dauerhaft"] = False

        pled = self._compute_pled(overrides)
        await self.coordinator.async_set_parameter("pled", pled)

    async def async_turn_on(self, **kwargs: object) -> None:
        try:
            await self._set_led(True)
        except Exception as exc:
            _LOGGER.error("Failed to turn on LED %s: %s", self.entity_description.key, exc)
            raise HomeAssistantError(
                f"Failed to turn on LED {self.entity_description.name or self.entity_description.key}: {exc}"
            ) from exc

    async def async_turn_off(self, **kwargs: object) -> None:
        try:
            await self._set_led(False)
        except Exception as exc:
            _LOGGER.error("Failed to turn off LED %s: %s", self.entity_description.key, exc)
            raise HomeAssistantError(
                f"Failed to turn off LED {self.entity_description.name or self.entity_description.key}: {exc}"
            ) from exc
