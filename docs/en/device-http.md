# Device HTTP and commands

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/device-http/)

These are Wi-Fi firmware endpoints. Platform accounts use the separate `/api/auth/...` API described under [platform integration](platform-hub.md).

## Access

Embedded WebUI uses same-origin HTTP. LAN clients query `info` and `capabilities` before selecting a device implementation. Device HTTP uses Basic authentication with username `admin` and the device Web password. Cross-origin browser access requires an allowed Origin and preflight; HTTPS-to-HTTP connections remain subject to browser mixed-content restrictions.

| Method and path | Purpose |
| --- | --- |
| `GET /api/v1/info` | Model, firmware and device identity |
| `GET /api/v1/status` | Status snapshot |
| `GET /api/v1/capabilities` | Features and supported actions |
| `GET /api/v1/config` | Public settings and password-presence flags, without plaintext passwords |
| `POST /api/v1/command` | JSON command envelope below |
| `GET /api/v1/config/backup` | Download a full binary backup; a Web password is required |
| `POST /api/v1/config/restore` | Restore a validated backup and schedule reboot |
| `POST /api/v1/mcu/exchange` | M1 only: raw binary MCU request/reply, request length 6–262 bytes |

Logs, schedules, memory and sensor diagnostics depend on the model. Older releases may lack newer endpoints.

## Command envelope

HTTP and TMCP use the same actions and JSON envelope:

```json
{"request_id":"web_123","action":"co2_source.get","params":{}}
```

```json
{"request_id":"web_123","code":"ok","message":"Success","data":{"source":"local","device_id":"","double_click":"none","revision":0,"valid":false,"button_events_supported":false}}
```

Match replies by `request_id`. Use the stable `code` for control flow and localized `message` for display. `ok` indicates a successful query; `accepted` indicates an accepted operation. Treat errors such as `invalid_params`, `busy`, `unsupported` and `conflict` as failures. Read `capabilities.actions` for the actual action list.

## M1 CO₂ source

`co2_source.get {}` returns:

| Field | Meaning |
| --- | --- |
| `source` | `local` for local SCD40; `mqtt` for an external sensor in this account |
| `device_id` | Lowercase 12-digit hex source ID; `""` for local |
| `double_click` | `none` or `switch_display` |
| `revision` | Configuration revision, 0..2147483647 |
| `valid`, `ppm` | Freshness result; omit `ppm` when invalid |
| `button_events_supported` | Sensor MCU declared extended button events |

Write all four configuration fields through `co2_source.set`, including the latest revision:

```json
{"request_id":"web_124","action":"co2_source.set","params":{"source":"mqtt","device_id":"123456abcdef","double_click":"switch_display","revision":0}}
```

Reject the device's own ID; `local` requires an empty ID. A stale revision returns `conflict`; success returns the incremented revision. OTA, pending reboot or Wi-Fi trial may return `busy`. Persistence failure does not publish a new configuration. Changing source clears cached remote data.

`co2_display.get` / `co2_display.set` manage mode, position, thresholds and interval. Display overrides do not modify physical HCHO, PM or CO₂ measurements. See [display sources](m1-display.md) for MCU behavior and button priority.
