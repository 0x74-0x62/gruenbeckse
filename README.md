# Grünbeck softliQ SE21 — Home Assistant Integration

A custom Home Assistant integration for the **Grünbeck softliQ SE21** water softener, connecting via the Grünbeck Cloud API with real-time SignalR push updates.

---

## Differences from hagruenbeck_cloud

This integration was built from scratch to support the **SE series** (softliQ SE21). It uses [hagruenbeck_cloud](https://github.com/p0l0/hagruenbeck_cloud) and [pygruenbeck_cloud](https://github.com/p0l0/pygruenbeck_cloud) by [@p0l0](https://github.com/p0l0) as a reference and reuses the `pygruenbeck_cloud` library for authentication and SignalR — but diverges significantly in the following areas:

### 1. Target device: SE series vs. SD series

`hagruenbeck_cloud` targets the **softliQ SD** series. The SE series has a different API surface, different field names, and a different device identifier format (`softliQ.SE/BSxxxxxxxx` instead of `softliQ.D/...`). Most SD-oriented library methods do not work correctly on SE devices.

### 2. Different measurement endpoint

| | hagruenbeck_cloud (SD) | This integration (SE21) |
|---|---|---|
| Measurement data | `GET /salt` | `GET /update` |
| Response fields | SD-specific model | `mtemp`, `mrescapa1`, `mlime`, `msaltrange`, … |

The library's `get_device_salt_measurements()` method returns incomplete or broken data on SE devices. This integration calls `GET /update` directly, which is the endpoint the official Grünbeck SE app uses.

### 3. Different regeneration command

| | hagruenbeck_cloud (SD) | This integration (SE21) |
|---|---|---|
| Trigger regeneration | `POST /regenerate` → 404 on SE | `POST /activate-boost-mode` → 200 OK |

`POST /regenerate` returns HTTP 404 on SE devices. The correct endpoint was identified by capturing traffic from the official iOS app with Charles Proxy.

### 4. `get_device_infos()` bypass

The library's `set_device_from_id()` / `get_device_infos()` call fails on SE devices because the API returns an empty `installedOn` date field, which the library cannot parse. This integration bypasses that call by assigning `api._device` directly after `get_devices()`.

### 5. Error and warning system

`hagruenbeck_cloud` tracks errors via a binary sensor attribute. This integration reads the `errors[]` array from `GET /api/devices/{id}` and exposes:

- **Binary sensor "Gerätestörung"** — any active error (with full error list as attributes)
- **Binary sensor "Salzvorrat gering"** — specifically `errorCode 26`, independent of the generic error flag
- **Sensor "Aktuelle Fehlermeldung"** — text of the most recent active error
- **Sensor "Aktueller Fehlercode"** — numeric code of the most recent active error

Note: `msaltrange` in `/update` does **not** reliably reflect the salt warning state on SE21 hardware. The `errors[]` array is the authoritative source.

### 6. Temperature sensor

The SE21 reports water temperature as `mtemp` in the `/update` response. This is not available in the SD series and has no equivalent in `hagruenbeck_cloud`.

### 7. Single-chamber device

The SE21 is a single-chamber device. Fields for exchanger 2 (`mRescapa2`, `mresidcap2`, `mstep2`, `mregpercent2`, `mflowreg2`) exist in the API response but are always 0. Corresponding entities are created but **disabled by default**.

Similarly, the SE21 has no physical flow meter — `mflow1` is always 0. The flow rate sensor exists but is disabled by default.

### 8. Direct REST calls instead of library abstraction

Rather than mapping SE data through the library's SD-oriented model, this integration calls the REST API directly using the library only for authentication (`_get_web_access_token()`) and SignalR transport (`connect()` / `listen()` / `disconnect()`).

---

## Supported device

- Grünbeck **softliQ SE21**

Other SE series devices may work but have not been tested.

---

## Features

### Sensors (enabled by default)
| Entity | Source field | Description |
|---|---|---|
| Weichwasser gesamt | `mcountwater1` | Total softened water (m³) |
| Kapazität | `mresidcap1` | Remaining capacity (%) |
| Verbleibende Kapazität | `mrescapa1` | Remaining capacity (L) |
| Regenerationen | `mcountreg` | Total regeneration count |
| Regenerationsschritt | `mregstatus` | Current regeneration step |
| Salzverbrauch | `msaltusage` | Salt consumption (kg) |
| Salzreichweite | `msaltrange` | Salt level status (ok/low) |
| Wasserhärte | `mlime` | Soft water hardness (°dH) |
| Temperatur | `mtemp` | Water temperature (°C) |
| Nachfüllwasser | `mcountwatertank` | Make-up water volume (L) |
| Kapazitätswert | `mcapacity` | Capacity figure |
| Nächste Regeneration | `calcRegMo1` | Next scheduled regeneration time |

### Binary Sensors (enabled by default)
| Entity | Description |
|---|---|
| Gerätestörung | Any active device error |
| Salzvorrat gering | Salt low warning (errorCode 26) |

### Controls
| Entity | Type | Default | Description |
|---|---|---|---|
| Regeneration starten | Button | enabled | Triggers `POST /activate-boost-mode` |
| Manueller Regenerationsmodus | Switch | disabled | `pregmode` parameter |
| Signalton | Switch | disabled | `pbuzzer` parameter |
| LED-Modus | Number (0–8) | disabled | `pled` parameter |
| LED-Helligkeit | Number (%) | disabled | `pledbright` parameter |
| Weichwasser-Sollwert | Number (°dH) | disabled | `psetsoft` parameter |
| Rohwasserhärte | Number (°dH) | disabled | `prawhard` parameter |
| Regenerationszähler zurücksetzen | Button | disabled | `pclearcntreg` |
| Wasserzähler zurücksetzen | Button | disabled | `pclearcntwater` |
| Fehlerspeicher löschen | Button | disabled | `pclearerrmem` |
| Regenerationszeiten (21×) | Time | disabled | Per-day schedule slots (7 days × 3 slots) |

---

## Requirements

- Home Assistant 2023.x or newer
- `pygruenbeck_cloud==1.3.3`
- A Grünbeck Cloud account with an SE21 device registered

---

## Installation

1. Copy the `custom_components/gruenbeck_se21` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Grünbeck SE21**.
4. Enter your Grünbeck Cloud credentials (e-mail and password).

---

## Credits

- [hagruenbeck_cloud](https://github.com/p0l0/hagruenbeck_cloud) by [@p0l0](https://github.com/p0l0) — SD series integration, used as reference
- [pygruenbeck_cloud](https://github.com/p0l0/pygruenbeck_cloud) by [@p0l0](https://github.com/p0l0) — Python library for authentication and SignalR
