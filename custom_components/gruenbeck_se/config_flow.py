"""Config flow for Grünbeck softliQ SE."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_DEVICE_ID, DOMAIN, DEFAULT_SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS
        ): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)


async def _get_se_devices(hass: HomeAssistant, username: str, password: str) -> list:
    from pygruenbeck_cloud import PyGruenbeckCloud

    api = PyGruenbeckCloud(username=username, password=password)
    try:
        devices = await api.get_devices()
    except Exception as exc:
        raise CannotConnect(str(exc)) from exc

    se_devices = [d for d in devices if getattr(d, "is_softliq_se", lambda: False)()]
    if not se_devices:
        _LOGGER.warning("No SE devices found. All devices: %s", [d.id for d in devices])
        raise NoDevicesFound
    return se_devices


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Grünbeck SE."""

    VERSION = 1
    _devices: list = []
    _user_input: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._devices = await _get_se_devices(
                    self.hass, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoDevicesFound:
                errors["base"] = "no_devices"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                self._user_input = user_input
                if len(self._devices) == 1:
                    device = self._devices[0]
                    await self.async_set_unique_id(device.serial_number)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=device.name or device.serial_number,
                        data={**user_input, CONF_DEVICE_ID: device.id},
                    )
                return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            idx = int(user_input[CONF_DEVICE_ID])
            device = self._devices[idx]
            await self.async_set_unique_id(device.serial_number)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=device.name or device.serial_number,
                data={**self._user_input, CONF_DEVICE_ID: device.id},
            )

        options = {str(i): d.id for i, d in enumerate(self._devices)}
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)}),
        )


class CannotConnect(HomeAssistantError):
    pass


class NoDevicesFound(HomeAssistantError):
    pass


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Grünbeck SE."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                }
            ),
        )
