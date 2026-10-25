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
| `POST /api/v1/ota/convert` | Explicit signed conversion to `hub`, only on DAIKIN `full` declaring conversion support; see below |
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

## DAIKIN partition diagnostics

DAIKIN firmware supporting this extension includes read-only `status.ota_partitions` in its status object. In a `status.get {}` command reply, the path is `data.ota_partitions`. This diagnostic field is optional; clients must handle its absence on other models or older firmware.

| Field | JSON type and meaning |
| --- | --- |
| `running` | String or null; label of the running application partition, or null when unavailable |
| `running_size` | Nonnegative integer; running application partition capacity in bytes; 0 when `running:null` |
| `next` | String or null; label of the SDK-selected next OTA target partition, or null when no target is available |
| `next_size` | Nonnegative integer; OTA target partition capacity in bytes; 0 when `next:null` |
| `entries` | Array of objects enumerating all SDK-visible application and data partitions in the device's installed partition table |
| `entries[].label` | String; partition label |
| `entries[].type` / `entries[].subtype` | Nonnegative integers; ESP-IDF partition type/subtype identifiers |
| `entries[].address` | Nonnegative integer; partition starting byte offset in Flash |
| `entries[].size` | Nonnegative integer; partition capacity in bytes |

All numbers are JSON decimal numbers, not hexadecimal strings. Labels, counts and capacities come from the installed partition table, independently of the build CSV; do not assume labels are always `app0` / `app1`. The object contains no Flash contents or credentials. It describes the current layout without switching OTA layouts or rewriting the partition table, and does not establish that an image is installed or suitable to write.

Implementation: `otaPartitionStatus()` and `state()` in `firmware/DAIKIN/src/commands.inc`.

Optional sibling status fields `minimum_free_memory` (lowest free heap since boot) and `max_free_block` (largest currently allocatable contiguous heap block) are nonnegative integers in bytes, alongside `free_memory`; clients must handle their absence.

### Hub byte-addressable heap

Supporting DAIKIN `hub` firmware adds three optional, read-only nonnegative JSON integers under the status object's `hub`, or `data.hub` in a `status.get {}` reply. All sizes are bytes and use the combined ESP-IDF capabilities `MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT`: internal memory accessible through byte reads and writes.

| Field in `data.hub` | Meaning |
| --- | --- |
| `free_byte_heap` | Total currently free heap with these capabilities |
| `largest_byte_block` | Largest currently allocatable contiguous block with these capabilities |
| `min_byte_heap` | SDK low-water statistic since boot: the sum of matching regions' minimum free sizes |

Regional low-water marks can occur at different times, so `min_byte_heap` need not equal the lowest simultaneous total. The existing sibling `free_memory`, `minimum_free_memory` and `max_free_block` retain their original ESP getter semantics; they are not aliases for these capability-specific values. Clients must tolerate missing `hub` or missing fields on older firmware and other variants. Do not apply these ESP32 meanings to other device models.

See the [fixed implementation](https://github.com/phicomm-io/iotcloud-community-firmware/blob/a555e6de08e40d44a4a6cf0896c7cc1581540f76/DAIKIN/src/commands.inc#L63-L67), [SDK heap reference](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/system/mem_alloc.html) and [Hub connection admission](platform-hub.md#hub-memory-diagnostics). These optional diagnostics do not change required contract fields or consumer pins.

### Reset reason

DAIKIN firmware supporting this diagnostic may include read-only `status.reset_reason`, or `data.reset_reason` in a `status.get {}` reply. It is a nonnegative JSON integer from `unsigned(esp_reset_reason())`, describing the last reset. Older firmware may omit the field; absence means the diagnostic is unavailable.

The following values belong to ESP-IDF 4.4.7's `esp_reset_reason_t` for DAIKIN's ESP32. They are not a shared reset-reason enumeration across device models or SDKs. Preserve unrecognized values as unknown diagnostics. See the [official SDK reference](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/system/system.html#reset-reason) and [version-pinned enum definition](https://github.com/espressif/esp-idf/blob/38eeba213aa695aabfd6d89aa9f5078dbe5a94c3/components/esp_system/include/esp_system.h#L41-L53).

| Number | SDK enum | Meaning |
| --- | --- | --- |
| 0 | `ESP_RST_UNKNOWN` | Undetermined reason |
| 1 | `ESP_RST_POWERON` | Power-on event |
| 2 | `ESP_RST_EXT` | External-pin reset; not applicable to ESP32 |
| 3 | `ESP_RST_SW` | Software restart through `esp_restart()` |
| 4 | `ESP_RST_PANIC` | Exception or panic |
| 5 | `ESP_RST_INT_WDT` | Interrupt watchdog |
| 6 | `ESP_RST_TASK_WDT` | Task watchdog |
| 7 | `ESP_RST_WDT` | Other watchdog |
| 8 | `ESP_RST_DEEPSLEEP` | Wake from deep sleep |
| 9 | `ESP_RST_BROWNOUT` | Brownout reset |
| 10 | `ESP_RST_SDIO` | SDIO reset |

Implementation: [DAIKIN status diagnostic](https://github.com/phicomm-io/iotcloud-community-firmware/blob/508dfed3597bb64bdfb3f29e10f2ee46c90189c2/DAIKIN/src/commands.inc#L28). This optional diagnostic does not change required contract fields or require consumers to update their existing specification pin.

## Explicit DAIKIN full → hub conversion

This is a development extension without a formal release. Supporting `full` firmware declares `data.ota_variant_conversion:"full-to-hub"` in `capabilities.get {}` replies. Do not attempt conversion without that declaration. Support does not establish that any Hub image fits the device's installed OTA slot.

Set a local device Web password first. Authenticate as Basic `admin` with that password, then send a complete `PHOTA001` signed binary to the dedicated endpoint:

```http
POST /api/v1/ota/convert
Authorization: Basic <base64(admin:device-Web-password)>
Content-Type: application/octet-stream
X-IoTCloud-Target-Variant: hub
X-IoTCloud-Confirm: full-to-hub

<complete PHOTA001 signed binary>
```

Both confirmation header values must match exactly. Local Hub owner sessions and upstream account sessions cannot replace device Basic authentication. The current configuration must be healthy, with no active OTA, pending command or scheduled reboot; configuration recovery blocks conversion.

Check application payload size against the actual next OTA partition, independently of the build CSV. The application prefix must match DAIKIN hardware, project and target `hub` identity at fixed offsets; finding identity strings elsewhere is insufficient. Check the fixed prefix and authenticate the envelope against a trusted signing key before erasing the inactive slot. After receiving the complete file, verify the signed payload digest by reading the entire staged payload from Flash, then read and verify the fixed identity again. Select the new boot partition only after every check passes.

| Positive/negative case | Result |
| --- | --- |
| Supporting `full`, correct password authentication and confirmation headers, healthy and idle, signed Hub image fits and passes all checks | HTTP 202, `{"code":"accepted"}`; schedule reboot |
| No device Web password is configured | HTTP 403, `set_web_password_first` |
| Device Web password exists but Basic authentication is missing or incorrect | HTTP 401, `unauthorized` |
| Missing or incorrect confirmation header values | HTTP 400, `invalid_params` |
| Configuration recovery is active | HTTP 409, `migration_required` |
| Active OTA, pending command or scheduled reboot | HTTP 409, `busy` |
| Running identity cannot select the explicit Full-to-Hub target | HTTP 409, `unsupported_conversion` |
| Actual slot too small, missing/invalid signature, digest/readback mismatch or fixed identity is not the target Hub | HTTP 400, `invalid_image`; do not activate |
| Different variant sent to ordinary `/api/v1/ota/upload` or `/api/v1/ota/upload-unsigned`, even with conversion headers | HTTP 400, `invalid_image`; ordinary endpoints preserve the running variant |
| `hub` requests conversion to `full` | No conversion endpoint on Hub; reject cross-variant ordinary uploads because Hub's larger configuration is incompatible |

Conversion preserves the partition table and ordinary configuration, including shared Wi-Fi, MQTT and device Web passwords. Initial Hub setup still requires the original device Web password; HAP defaults off. Installing the image neither creates a local owner nor completes HomeKit pairing. Conversion does not enlarge OTA slots: a factory 1.5 MiB slot still rejects larger images. HTTP 202 confirms verification and a scheduled reboot; reconnect and read `info` / `status` with `firmware_variant:"hub"` to establish that Hub is running.

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

<a id="m1-dual-display-api"></a>

## M1 dual user display API

Development contract `m1-display-v2` adds `display_source.get {}`, `display_source.set` and `display_data.set`. Require these actions in `capabilities.actions`; their presence does not prove sensor MCU support. `mcu.version.get` adds `display_source_schema` (2 or 0) and `dual_display_source_supported`. Existing `display_source_supported` still means scalar schema1. Control also requires [dual negotiation and readback](m1-display.md).

`display_source.set` replaces both persisted lane configurations with the latest revision. slot0 is HCHO, slot1 PM2.5; include each exactly once. Defaults are selected_source=`original`, double_click=`none`; each lane uses source=`none`, device_id=`""`, metric=`custom`, unit=`""`, decimals0, scale1, ttl_seconds20 and color=`{"mode":"fixed","value":"off"}`.

```json
{"request_id":"display_cfg_1","action":"display_source.set","params":{"revision":0,"selected_source":"user","double_click":"switch_display","lanes":[{"slot":0,"source":"mqtt","device_id":"001122334455","metric":"power","unit":"W","decimals":2,"scale":1000,"ttl_seconds":15,"color":{"mode":"thresholds","low":100,"high":1000}},{"slot":1,"source":"api","device_id":"","metric":"custom","unit":"%","decimals":1,"scale":1,"ttl_seconds":10,"color":{"mode":"fixed","value":"green"}}]}}
```

| Configuration field | Rule |
| --- | --- |
| `revision` | Strict JSON integer 0..2147483647, compare-and-swap; advances on success |
| `selected_source` | `original` / `user`, global for both lanes |
| `double_click` | `none` / `switch_display`; cancel a ringing alarm first without toggling |
| `lanes[].source` | `none` / `local` / `mqtt` / `api`; none always retains original readings |
| `device_id` | mqtt requires an external lowercase 12-hex ID in the same account, excluding self; otherwise empty |
| `metric`, `unit` | Fixed pairs below; custom only for api/none, and none requires custom with empty unit |
| `decimals`, `scale` | Integers 0..2 and 1 or1000; display `value / scale`, without changing physical units or alarms |
| `ttl_seconds` | Integer1..60 maximum data lifetime; physical sources retain stricter freshness limits |
| `color` | fixed requires value off/red/green/yellow; thresholds requires finite low<high, comparing unscaled values for green/yellow/red |

| Metric | Unit | Sources and range |
| --- | --- | --- |
| `temperature` | `°C` | local/mqtt/api; physical -40..125, negative values cannot render in generic positions and fall back |
| `humidity` | `%` | local/mqtt/api; 0..100 |
| `pm25`, `formaldehyde` | `µg/m³`, `mg/m³` | local/mqtt/api; finite, nonnegative |
| `co2` | `ppm` | local/mqtt/api; 1..65535, local requires real SCD40 support |
| `pressure` | `Pa` | local/mqtt/api; finite, nonnegative; numerically convert centi-Pa/hPa before labeling Pa |
| `power`, `energy` | `W`, `kWh` | mqtt/api; finite, nonnegative; current new TC1 feed publishes power only, without claiming energy |
| `tvoc`, `pm10` | `ppb`, `µg/m³` | mqtt/api; finite, nonnegative, according to actual producer fields |
| `fan_speed_percent` | `%` | A1 mqtt or api; finite0..100; A1 effective main-fan output percentage, not measured RPM, including fresh-air variants |
| `custom` | Allowlist | api only; unit is `""`, `°C`, `%`, `µg/m³`, `mg/m³`, `ppm`, `Pa`, `W`, `kWh` or `ppb` |

Local means this M1, permitting only climate, PM2.5, HCHO, CO₂ and pressure. Missing capability or fresh samples makes it invalid. MQTT consumes only the same-account [typed feed](mqtt.md#sensor-values-v1), never arbitrary topics, URLs or JSONPath. none permits only custom/empty unit and is not writable. Reject unknown fields, wrong types, mismatching units, duplicate slots and low>=high.

Each lane has three nonnegative digits; encoding outside0..999 restores only that lane. Firmware derives native legends from the real slot, metric, unit and scale1. The glass has no selectable W, ℃ or % glyphs. Clients must explain logical units and scale; see [representation limits](m1-display.md#display-representation).

`display_data.set` leases RAM data only to a lane configured as api. Require matching configuration revision/unit and TTL no greater than its configured limit. Optional color directly overrides this lease. A value write requires value, unit and1..60-second TTL. Clearing has a separate shape without fake zero:

```json
{"request_id":"display_value_1","action":"display_data.set","params":{"revision":1,"slot":1,"value":45.6,"unit":"%","ttl_seconds":10,"color":"yellow"}}
{"request_id":"display_clear_1","action":"display_data.set","params":{"revision":1,"slot":1,"ttl_seconds":0}}
```

Both use existing HTTP Basic or authorized MQTT command authentication; reject retained commands. Repeating request_id returns the existing result without renewing a lease. Public sensor fields cannot write api lanes. Values/leases never persist to Flash or replay after reboot. `accepted` is not display confirmation.

GET keeps configuration at the root: revision, selected_source, double_click, lanes. Read-only `runtime` is separate and must not be sent back to SET:

| Runtime field | Meaning |
| --- | --- |
| `profile` | Active `legacy` / `dual` scheduler |
| `selected_source` | Actual original/user selection including a double-click RAM override, rebuilt on configuration change or reboot |
| `mcu_supported` | Explicit dual schema2 negotiation, beyond scalar support |
| `confirmed`, `confirmation` | Fresh independent MCU readback matches; `mcu_readback`, `pending_mcu_readback` or `requires_mcu_upgrade` |
| `lanes[].slot/valid/value/unit` | Resolved reading per position; unknown/invalid value is null |
| `age_ms`, `remaining_ttl_seconds` | Sample age or null; remaining0..60 seconds |
| `effective`, `reason` | Eligibility for user overlay; reason ok/disabled/missing/stale/offline/invalid/out_of_range/unsupported |
| `number/format/color` | Encoded output or null; color is a string enum |
| `confirmed` | This lane matches an independent MCU query, without optical LCD proof |

Global `confirmed` is true exactly when `profile=dual`, the MCU is supported and both lanes are confirmed; `confirmation` is then `mcu_readback`. A confirmed clear may have `valid=false` and zero remaining lease: value validity and confirmation are separate.

With `valid=true`, value, age and encoded fields are present, the remaining lease is positive and `reason=ok`. Otherwise value and encoded fields are null and the remaining lease is zero. `effective=true` also requires this lane's MCU readback to be confirmed.

After saving, independently GET and compare revision/full configuration. After writing a value, GET and compare that lane's valid/value/unit/lease; MCU confirmation still requires independent UART queries. Old MCUs may retain desired settings without claiming dual control. Expiry preserves desired selection and restores only the affected position. Without reliable offline events, use TTL rather than inventing offline detection.

Successful new SET persistently selects dual. Successful legacy CO₂ SET selects legacy and preserves dual configuration. Commit profile/settings together; conflicts, busy and storage_error roll back completely. Dual configuration appends M1 storagev9; see [v8 migration and backups](configuration.md#m1-display-storage-v9).

## M1 sensor reminders

`alarm.get {}` reads thresholds and optional sensor-buzzer switches. `alarm.set` requires `sensor` (`hcho` / `pm25`), `yellow` (integer 0..65535), `red` (integer 1..65535 and at least `yellow`), and the latest `revision` (integer 0..2147483647). Optional `buzzer_enabled` must be a JSON boolean and changes only the selected sensor; omission preserves its setting. Reject unknown fields, strings/floats in integer fields and numbers in boolean fields.

```json
{"request_id":"web_alarm_1","action":"alarm.set","params":{"sensor":"pm25","yellow":75,"red":150,"revision":0,"buzzer_enabled":false}}
```

Successful persistence returns `accepted` and the full configuration with incremented revision. Revision mismatch, exhausted revision or occupied runtime returns `busy`; storage failure returns `storage_error` and rolls back completely. Threshold units remain `main_controller_raw_u16`; do not infer unit conversions from sensor names. Old configurations and unknown extension schemas migrate both desired buzzer switches to default OFF while preserving thresholds and revision.

| `alarm.get` data field | Meaning |
| --- | --- |
| `revision` | Current configuration revision |
| `hcho_configured` / `pm25_configured` | Whether each sensor's thresholds were configured |
| `hcho_yellow` / `hcho_red` / `pm25_yellow` / `pm25_red` | Sensor thresholds |
| `hcho_buzzer_enabled` / `pm25_buzzer_enabled` | Persisted desired switches, default false |
| `buzzer_supported` / `mcu_alarm_schema` | Negotiated MCU support and schema 0 / 1 |
| `buzzer_confirmed` | A fresh independent read matches the current revision and desired mask |
| `buzzer_confirmation` | `mcu_readback` / `pending_mcu_readback` / `requires_mcu_upgrade` |
| `mcu_hcho_buzzer_enabled` / `mcu_pm25_buzzer_enabled` | Actual switches; null when unknown or readback is at least 15 seconds old |
| `mcu_buzzer_mask` | Actual mask 0..7; null when unknown |
| `sensor_alarm_active` | Sensor reminder condition from the MCU's latest poll; null when unknown, not sound sensing |
| `uart_sent` / `confirmation` | Compatible threshold-send result; `confirmation` remains `uart_send_only` |
| `unit` | `main_controller_raw_u16` |

Wi-Fi persists desired settings, sends [OP `14`](m1-uart.md#op-14-optional-sensor-buzzer) after capability negotiation, then independently reads and verifies them. A write reply cannot set `buzzer_confirmed:true`. Threshold `uart_sent:true` also does not establish buzzer readback. Old MCUs still save desired settings but return `buzzer_supported:false`, `buzzer_confirmation:"requires_mcu_upgrade"` and null actual fields. Clients must distinguish desired OFF from actual unknown, without claiming that the buzzer was silenced.
