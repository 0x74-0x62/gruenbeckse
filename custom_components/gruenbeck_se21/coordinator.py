"""DataUpdateCoordinator for Grünbeck softliQ SE21."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from yarl import URL

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DEVICE_ID, DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

_API_HOST = "prod-eu-gruenbeck-api.azurewebsites.net"
_API_VERSION = "2024-05-02"

_PARAM_KEYS = (
    "pregmode", "pbuzzer",
    "pled", "pledbright",
    "psetsoft", "prawhard",
    "pregsu1", "pregsu2", "pregsu3",
    "pregmo1", "pregmo2", "pregmo3",
    "pregdi1", "pregdi2", "pregdi3",
    "pregmi1", "pregmi2", "pregmi3",
    "pregdo1", "pregdo2", "pregdo3",
    "pregfr1", "pregfr2", "pregfr3",
    "pregsa1", "pregsa2", "pregsa3",
)


class GruenbeckSE21Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator with persistent SignalR connection and SE-native REST polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        device_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self._username = username
        self._password = password
        self._device_id = device_id
        self.api: Any = None
        self._unsub_stop: Any = None

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    async def _init_api(self) -> None:
        from pygruenbeck_cloud import PyGruenbeckCloud

        api = PyGruenbeckCloud(username=self._username, password=self._password)
        devices = await api.get_devices()
        device = next((d for d in devices if d.id == self._device_id), None)
        if device is None:
            raise UpdateFailed(f"Device {self._device_id} not found in account")
        # Bypass set_device_from_id() — get_device_infos() fails on SE (empty date field).
        api._device = device
        self.api = api

    def _api_url(self, path_suffix: str) -> URL:
        return URL.build(
            scheme="https",
            host=_API_HOST,
            path=f"/api/devices/{self._device_id}/{path_suffix}",
            query={"api-version": _API_VERSION},
        )

    def _device_url(self) -> URL:
        return URL.build(
            scheme="https",
            host=_API_HOST,
            path=f"/api/devices/{self._device_id}",
            query={"api-version": _API_VERSION},
        )

    async def _api_headers(self) -> dict[str, str]:
        token = await self.api._get_web_access_token()
        return {
            "Host": _API_HOST,
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {token}",
        }

    async def _fetch_update(self) -> dict[str, Any]:
        """GET /update — SE-native endpoint for all current measurements."""
        headers = await self._api_headers()
        result = await self.api._http_request(
            url=self._api_url("update"),
            headers=headers,
            method=aiohttp.hdrs.METH_GET,
        )
        if not isinstance(result, dict):
            raise UpdateFailed(f"Unexpected /update response type: {type(result)}")
        return result

    async def _fetch_device_info(self) -> dict[str, Any]:
        """GET /api/devices/{id} — firmware version, device status."""
        headers = await self._api_headers()
        result = await self.api._http_request(
            url=self._device_url(),
            headers=headers,
            method=aiohttp.hdrs.METH_GET,
        )
        return result if isinstance(result, dict) else {}

    async def _fetch_parameters(self) -> dict[str, Any]:
        """GET /parameters — all device settings."""
        headers = await self._api_headers()
        result = await self.api._http_request(
            url=self._api_url("parameters"),
            headers=headers,
            method=aiohttp.hdrs.METH_GET,
        )
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # WebSocket / SignalR
    # ------------------------------------------------------------------

    async def _listen_websocket(self) -> None:
        """Background task: connect and block on the SignalR message loop."""
        try:
            await self.api.connect()
        except Exception as exc:
            _LOGGER.warning("SignalR connect failed: %s", exc)
            return

        async def _on_ha_stop(_: Event) -> None:
            self._unsub_stop = None
            await self.api.disconnect()

        self._unsub_stop = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, _on_ha_stop
        )

        try:
            await self.api.listen(callback=self._on_ws_update)
        except Exception as exc:
            _LOGGER.debug("SignalR listen ended: %s", exc)
        finally:
            await self.api.disconnect()
            if self._unsub_stop:
                self._unsub_stop()
                self._unsub_stop = None

    @callback
    def _on_ws_update(self, device: Any) -> None:
        """SignalR push received — refresh measurement data only."""
        self.hass.async_create_task(self._fetch_and_notify())

    async def _fetch_and_notify(self) -> None:
        try:
            raw = await self._fetch_update()
            # Merge measurement update into existing data to preserve info/params.
            merged = dict(self.data) if self.data else {}
            merged.update(self._update_to_dict(raw))
            self.async_set_updated_data(merged)
        except Exception as exc:
            _LOGGER.debug("Post-WebSocket /update fetch failed: %s", exc)

    # ------------------------------------------------------------------
    # Periodic update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if self.api is None:
                await self._init_api()

            if not self.api.connected and self._unsub_stop is None:
                self.hass.async_create_background_task(
                    self._listen_websocket(),
                    "gruenbeck_se21_ws",
                )

            raw_update = await self._fetch_update()
            _LOGGER.debug(
                "SE21 /update: hasError=%s resid1=%s%%  flow1=%s L/min  temp=%s°C",
                raw_update.get("hasError"),
                raw_update.get("mresidcap1"),
                raw_update.get("mflow1"),
                raw_update.get("mtemp"),
            )

            try:
                raw_info = await self._fetch_device_info()
            except Exception as exc:
                _LOGGER.debug("Device info fetch failed: %s", exc)
                raw_info = {}

            try:
                raw_params = await self._fetch_parameters()
            except Exception as exc:
                _LOGGER.debug("Parameters fetch failed: %s", exc)
                raw_params = {}

            result: dict[str, Any] = {}
            result.update(self._update_to_dict(raw_update))
            result.update(self._info_to_dict(raw_info))
            result.update(self._params_to_dict(raw_params))
            return result

        except UpdateFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"Error communicating with Grünbeck Cloud: {exc}") from exc

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def async_regenerate(self) -> None:
        """Trigger manual regeneration via the SE-specific boost-mode endpoint."""
        headers = await self._api_headers()
        headers["Content-Type"] = "application/json"
        await self.api._http_request(
            url=self._api_url("activate-boost-mode"),
            headers=headers,
            method=aiohttp.hdrs.METH_POST,
            json_data={},
            expected_status_codes=[
                aiohttp.http.HTTPStatus.ACCEPTED,
                aiohttp.http.HTTPStatus.OK,
            ],
        )
        _LOGGER.debug("SE21 regeneration (boost mode) triggered")

    async def async_set_parameter(self, key: str, value: Any) -> None:
        """PATCH /parameters with a single {key: value} and refresh."""
        headers = await self._api_headers()
        headers["Content-Type"] = "application/json"
        await self.api._http_request(
            url=self._api_url("parameters"),
            headers=headers,
            method=aiohttp.hdrs.METH_PATCH,
            json_data={key: value},
            expected_status_codes=[aiohttp.http.HTTPStatus.OK],
        )
        _LOGGER.debug("SE21 parameter set: %s = %r", key, value)
        try:
            raw_params = await self._fetch_parameters()
            if self.data:
                merged = dict(self.data)
                merged.update(self._params_to_dict(raw_params))
                self.async_set_updated_data(merged)
        except Exception as exc:
            _LOGGER.debug("Post-set parameter refresh failed: %s", exc)

    # ------------------------------------------------------------------
    # Data mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _update_to_dict(d: dict[str, Any]) -> dict[str, Any]:
        """Map /update JSON → coordinator dict."""
        return {
            # Device state
            "has_error":                        d.get("hasError", False),
            # Water quantities (m³)
            "soft_water_quantity":              d.get("mcountwater1"),
            "make_up_water_volume":             d.get("mcountwatertank"),
            "remaining_amount_of_water":        d.get("mreswatadmod"),
            # Capacity
            "remaining_capacity_volume":        d.get("mrescapa1"),
            "remaining_capacity_volume_2":      d.get("mRescapa2"),
            "remaining_capacity_percentage":    d.get("mresidcap1"),
            "remaining_capacity_percentage_2":  d.get("mresidcap2"),
            "capacity_figure":                  d.get("mcapacity"),
            # Flow
            "current_flow_rate":                d.get("mflow1"),
            "current_flow_rate_2":              d.get("mflow2"),
            "blending_flow_rate":               d.get("mflowblend"),
            "regeneration_flow_rate_2":         d.get("mflowreg2"),
            # Temperature
            "temperature":                      d.get("mtemp"),
            # Salt
            "salt_range":                       d.get("msaltrange"),
            "salt_consumption":                 d.get("msaltusage"),
            # Regeneration
            "regeneration_counter":             d.get("mcountreg"),
            "regeneration_step":                d.get("mregstatus"),
            "regeneration_step_2":              d.get("mstep2"),
            "regeneration_percentage_2":        d.get("mregpercent2"),
            "regeneration_trigger":             d.get("iregtrig"),
            # Water quality
            "actual_value_soft_water_hardness": d.get("mlime"),
            # Not available from /update — show unavailable in HA
            "exhausted_percentage":             None,
            "flow_rate_peak_value":             None,
            "last_regeneration_exchanger":      None,
            "regeneration_remaining_time":      None,
            "next_service":                     None,
        }

    @staticmethod
    def _info_to_dict(d: dict[str, Any]) -> dict[str, Any]:
        """Map GET /devices/{id} → coordinator dict."""
        raw_errors = d.get("errors") or []
        active = [
            {
                "message": e.get("message"),
                "code":    e.get("errorCode"),
                "type":    e.get("type"),
                "date":    e.get("date"),
            }
            for e in raw_errors
            if isinstance(e, dict) and not e.get("isResolved", True)
        ]
        first = active[0] if active else {}
        return {
            "sw_version":           d.get("swVersion"),
            "hw_version":           d.get("hwVersionCl"),
            "device_status":        d.get("estatus"),
            "installed_on":         d.get("installedOn"),
            "next_regen_calc":      d.get("calcRegMo1"),
            # errorCode 26 = "Salzvorrat gering"
            "low_salt":             any(e["code"] == 26 for e in active),
            "active_errors":        active,
            "active_error_message": first.get("message"),
            "active_error_code":    first.get("code"),
        }

    @staticmethod
    def _params_to_dict(d: dict[str, Any]) -> dict[str, Any]:
        """Map GET /parameters → coordinator dict (prefixed param_*)."""
        result = {
            f"param_{key}": d[key]
            for key in _PARAM_KEYS
            if key in d
        }
        # Decode pled bitmask → 4 individual LED boolean keys.
        # pled=0: all off | pled=1: Dauerhaft (exclusive) | pled=2–8: n=pled-1, bits 0/1/2
        if "pled" in d:
            pled = int(d["pled"]) if d["pled"] is not None else 0
            if pled == 0:
                result["param_led_stoerung"]  = False
                result["param_led_meldung"]   = False
                result["param_led_durchfluss"] = False
                result["param_led_dauerhaft"] = False
            elif pled == 1:
                result["param_led_stoerung"]  = False
                result["param_led_meldung"]   = False
                result["param_led_durchfluss"] = False
                result["param_led_dauerhaft"] = True
            else:
                n = pled - 1
                result["param_led_stoerung"]  = bool(n & 1)
                result["param_led_meldung"]   = bool(n & 2)
                result["param_led_durchfluss"] = bool(n & 4)
                result["param_led_dauerhaft"] = False
        return result
