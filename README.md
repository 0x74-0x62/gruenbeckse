# Grünbeck softliQ SE Series (SE18/SE21/SE24) — Home Assistant Integration

> **⚠️ Disclaimer**
>
> This is a fork of the [bernd780/gruenbeckse21](https://github.com/bernd780/gruenbeckse21) repository. 


> **⚠️ Disclaimer**
>
> This integration was created by a hobbyist, not a professional software developer.
> It is provided **as-is, without any warranty or guarantee** of correctness, stability, or fitness for any purpose.
> **No support can be offered.**
>
> The author hopes that the SE series support implemented here finds its way into the original projects
> [hagruenbeck_cloud](https://github.com/p0l0/hagruenbeck_cloud) and/or [pygruenbeck_cloud](https://github.com/p0l0/pygruenbeck_cloud),
> where it would receive proper maintenance. Pull requests to those repositories are very welcome.

---

A custom Home Assistant integration for the **Grünbeck softliQ SE series (SE18, SE21, SE24)** water softeners.

> [!NOTE]
> Unlike the SD series, the SE series does not support real-time/push updates via the Grünbeck Cloud API. Consequently, this integration utilizes a polling approach to retrieve data.

---

## Differences from hagruenbeck_cloud

This integration was built from scratch to support the **SE series** (softliQ SE18/SE21/SE24). It uses [hagruenbeck_cloud](https://github.com/p0l0/hagruenbeck_cloud) and [pygruenbeck_cloud](https://github.com/p0l0/pygruenbeck_cloud) by [@p0l0](https://github.com/p0l0) as a reference and reuses the `pygruenbeck_cloud` library for authentication — but diverges significantly in the following areas:

### 1. Target device: SE series vs. SD series

`hagruenbeck_cloud` targets the **softliQ SD** series. The SE series has a different API surface, different field names, and a different device identifier format (`softliQ.SE/BSxxxxxxxx` instead of `softliQ.D/...`). Most SD-oriented library methods do not work correctly on SE devices.

### 2. Different measurement endpoint

| | hagruenbeck_cloud (SD) | This integration (SE) |
|---|---|---|
| Measurement data | `GET /salt` | `GET /update` |
| Response fields | SD-specific model | `mtemp`, `mrescapa1`, `mlime`, `msaltrange`, … |

The library's `get_device_salt_measurements()` method returns incomplete or broken data on SE devices. This integration calls `GET /update` directly, which is the endpoint the official Grünbeck SE app uses.

### 3. Different regeneration command

| | hagruenbeck_cloud (SD) | This integration (SE) |
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

Note: `msaltrange` in `/update` does **not** reliably reflect the salt warning state on SE hardware. The `errors[]` array is the authoritative source.

### 6. Temperature sensor

The SE series API reports water temperature as `mtemp` in the `/update` response (which is not available in the SD series). However, the physical temperature sensor is only present on the larger **softliQ:SE24** model, not on the SE18 and SE21. If the sensor is not physically installed, the API returns a negative sentinel value (e.g., `-9`). This integration automatically filters out negative temperatures and disables the temperature sensor entity by default (it can be manually enabled for SE24 devices).

### 7. Single-chamber device / Exchanger 2

The SE18 and SE21 are single-chamber devices. Fields for exchanger 2 (`mRescapa2`, `mresidcap2`, `mstep2`, `mregpercent2`, `mflowreg2`) exist in the API response but are always 0. Corresponding entities are created but **disabled by default**.

The SE series uses an internal turbine-based water meter/pulse generator to track consumption and calculate real-time flow rate (`mflow1`). The **Durchfluss** (flow rate) sensor is enabled by default to show flow rate updates fetched during the update interval.

### 8. Direct REST calls instead of library abstraction

Rather than mapping SE data through the library's SD-oriented model, this integration calls the REST API directly using the library for authentication (`_get_web_access_token()`) and making the 5-step HTTP update calls.

---

## Supported devices

- Grünbeck **softliQ SE18**
- Grünbeck **softliQ SE21**
- Grünbeck **softliQ SE24**

Other SE series devices may work but have not been fully tested.

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
| Durchfluss | `mflow1` | Current flow rate (m³/h) |
| Nachfüllwasser | `mcountwatertank` | Make-up water volume (L) |
| Kapazitätswert | `mcapacity` | Capacity figure |
| Nächste Regeneration | `calcRegMo1` | Next scheduled regeneration time |

### Sensors (disabled by default)
| Entity | Source field | Description |
|---|---|---|
| Temperatur | `mtemp` | Water temperature (°C) — only on SE24 |
| Durchfluss 2 | `mflow2` | Flow rate exchanger 2 (m³/h) — only on double-chamber models |
| Verbleibende Kapazität 2 | `mRescapa2` | Remaining capacity exchanger 2 (L) — only on double-chamber models |
| Kapazität 2 | `mresidcap2` | Remaining capacity exchanger 2 (%) — only on double-chamber models |
| Regenerationsschritt 2 | `mstep2` | Regeneration status exchanger 2 — only on double-chamber models |
| Regeneration % 2 | `mregpercent2` | Regeneration percentage exchanger 2 — only on double-chamber models |
| Regenerationsdurchfluss 2 | `mflowreg2` | Regeneration flow rate exchanger 2 — only on double-chamber models |

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
- A Grünbeck Cloud account with an SE series device registered

---

## Installation

1. Copy the `custom_components/gruenbeck_se` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Grünbeck SE**.
4. Enter your Grünbeck Cloud credentials (e-mail, password, and desired update interval in seconds).

---

## Credits

- [hagruenbeck_cloud](https://github.com/p0l0/hagruenbeck_cloud) by [@p0l0](https://github.com/p0l0) — SD series integration, used as reference
- [pygruenbeck_cloud](https://github.com/p0l0/pygruenbeck_cloud) by [@p0l0](https://github.com/p0l0) — Python library for authentication and SignalR
