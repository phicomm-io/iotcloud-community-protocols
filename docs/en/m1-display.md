# M1 display sources and buttons

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/m1-display/)

Formatting and individual-lamp contract `m1-display-v3` uses additive `m1-uart-v4`. Existing dual schema 2 and scalar schema 1 retain their meanings. These are development interfaces without a formal release.

## M1 display v3

Slot0 is the HCHO region; slot1 is PM2.5. HCHO has a fixed decimal point after the first digit. PM supports integers only. `unit` in local/MQTT configuration describes the source's physical value; it cannot create ppm, W or % glyphs on the glass. `display.show_label` enables the original HCHO/PM2.5 legend, while `display.show_unit` independently enables the original mg/m³ / µg/m³ unit. Both are required booleans, initially false for custom/external data.

The following modes transform local/MQTT physical inputs. Direct API writes instead supply the digit register, three flags and all nine lamps explicitly.

| `display.mode` | HCHO presentation | Example / limit |
| --- | --- | --- |
| `integer` | Round to the nearest integer | 123.5 → `124`; maximum `999`; the only PM mode |
| `auto_kilo` | Integer below 1000; otherwise divide by 1000 and show x.xx | 1234 → `1.23`; scaled maximum `9.99` |
| `decimal_2` | Round to the nearest hundredth, fixed x.xx | 1.2351 → `1.24`; maximum `9.99` |
| `decimal_1` | Round to the nearest tenth with a trailing zero | 1.251 → `1.30`; maximum `9.90` |
| `milli` | Divide by 1000 and round to the nearest hundredth | 1234 → `1.23`; maximum `9.99` |

Physical input and arithmetic use float32; positive ties round upward. Positive display overflow remains valid and saturates at the mode's limit. Negative, nonfinite or metric-invalid data restores that region's original reading. Thresholds compare the physical input before conversion. Independent expiry, the global original/user selector, double-click switching and alarm priority retain their existing behavior.

Each region has three physical positions, left/middle/right, each with independent red/green/yellow segments: nine segments per region. Multiple colors may be enabled at one position. Fixed color uses this complete shape:

```json
{"mode":"fixed","lamps":[{"red":true,"green":false,"yellow":false},{"red":false,"green":true,"yellow":false},{"red":true,"green":false,"yellow":true}]}
```

Array order is physical left/middle/right. Each object contains exactly the three booleans. Threshold mode remains `{"mode":"thresholds","low":1000,"high":2000}`: all three positions green below low, yellow in [low, high), red at/above high; require low<high. Direct API writes require this complete lamp array and use it exactly, bypassing configured thresholds. Display lamps never replace sensor measurements or alarm inputs.

### Glass layout: 19 display groups

PM2.5 is on the left and HCHO on the right. Each `8` below illustrates a digit position that exists on the glass; it does not specify sensor accuracy, UART precision or decimal places in the existing temperature/humidity driver. The climate regions are separate from the two generic display slots above.

| Group | Position | Glass content / digit positions |
| --- | --- | --- |
| 1 | Top | Date `8888-88-88` |
| 2 | Top | Time `88:88` |
| 3 | Top | Wi-Fi icon and `×` status segment |
| 4 | Middle left | `PM2.5` label |
| 5 | Middle left | PM2.5 digits `888`; slot1 accepts integers only |
| 6 | Middle left | `µg/m³` unit |
| 7 | Below PM2.5 digits | Three positions, left/middle/right × red/green/yellow: nine lamp segments |
| 8 | Middle right | `甲醛` (HCHO) label |
| 9 | Middle right | HCHO digits `8.88`; fixed decimal after the first digit, optionally hidden |
| 10 | Middle right | `mg/m³` unit |
| 11 | Below HCHO digits | Three positions, left/middle/right × red/green/yellow: nine lamp segments |
| 12 | Bottom temperature region | Thermometer icon |
| 13 | Bottom temperature region | `温度` (temperature) label |
| 14 | Bottom temperature region | Digit positions `88.8` |
| 15 | Bottom temperature region | `°C` unit |
| 16 | Bottom humidity region | Water-drop icon |
| 17 | Bottom humidity region | `湿度` (humidity) label |
| 18 | Bottom humidity region | Digit positions `88.8` |
| 19 | Bottom humidity region | `%` unit |

### UART flags and lamp mapping

OP `00` D13 / f18 remains 2. No old capability byte gains a new meaning. After checking it, use read-only OP26 / `0x1a` to probe schema3. Unsupported/invalid-operation replies or failed queries from old MCUs require bounded probing, no OP24/25 writes and `requires_mcu_upgrade`.

| Decimal OP / hexadecimal | Arguments | Effect |
| --- | --- | --- |
| 24 / `18` write | A0–1 number BE16 0..999; A2 format; A3–4 lamps BE16 0..511; A5 TTL0..60; A6 slot0..1 | Update only this formatted cache; TTL0 clears it |
| 25 / `19` select | A0=0 original / 1 user; A1..6=0 | Explicitly activate formatted profile, including original selection |
| 26 / `1a` query | A0=slot; A1..6=0 | Read the cache, saved selection and profile-active flag |

Format bit0 is the fixed HCHO decimal, bit1 the original label, bit2 the original unit; bits3..7 are zero. PM forbids bit0. Formatted caches are independent of scalar/dual caches. Writes and queries never select a profile. Old decimal OP10/18/22 (hex `0a`/`12`/`16`) explicitly reclaim legacy CO₂/scalar/dual ownership respectively. Expert overrides, OTA and reset keep their priorities.

Lamp bits0..2 are red left/middle/right, bits3..5 green, bits6..8 yellow. Uniform red=`0x007`, green=`0x038`, yellow=`0x1c0`; the mixed example above is `0x115`. LCD RAM offsets are red `0x0c`, green `0x13`, yellow `0x12`. HCHO position bits are `0x10/0x20/0x40`; PM bits are `0x80/0x01/0x04`. Clear and replace only the chosen region's bits, preserving every other bit in all three color bytes.

Example: write HCHO `1.23`, mixed lamps and a 20-second lease, select user readings, then query independently:

```text
23 70 18 01 00 7b 01 01 15 14 00 21
23 70 19 02 01 00 00 00 00 00 00 21
23 70 1a 03 00 00 00 00 00 00 00 21
```

Successful write/select data is all zero. An OP26 reply uses absolute offsets: f5=schema3, f6=cached selection, f7=effective, f8=slot, f9–10=number, f11=format, f12–13=lamps, f14=remaining TTL rounded up (0..60), f15=formatted profile active, f16..18=0. Effective requires active profile, user selection and TTL>0.

An OP26 reply alone never confirms selection. Wi-Fi must first receive the matching OP25 ACK for its current configuration generation, then independently query both lanes and match f15=1, selection, encoded value, flags, lamps and fresh TTL. A cached v2 reply cannot confirm formatted control. See [display_profile API](device-http.md#m1-display_profile-api) for configuration, runtime and compatibility views, and [contracts and vectors](contracts.md) for machine artifacts.

<a id="dual-lane-schema-2"></a>

## Compatible dual-lane schema 2

HCHO position `slot=0` and PM2.5 position `slot=1` have independent values, formats, colors and leases. One global selector changes both original/user sources together, including a single double click. A lane configured as `none`, missing, expired, offline or outside its representable range returns only that position to its original reading. Expiry preserves the global desired selection; fresh data may restore that lane.

Wi-Fi MCU resolves sources, physical units, scaling and colors. Sensor MCU renders encoded data. User values must never replace physical measurements, alarm inputs or physical sensor publications. See [dual display API](device-http.md#m1-dual-display-api) and [typed sensor feed](mqtt.md#sensor-values-v1).

### Capability and operations

New writes require OP `00` D13 / f18=`2`. D11 / f16 remains scalar schema `1`; D12 / f17 remains the independent sensor alarm schema. Outer extension protocol D0 remains `2`. New Wi-Fi also verifies schema 2 through read-only OP `17`; absent/unknown capability or failed probing leaves original readings without new writes.

OP numbers below are hexadecimal (`15`/`16`/`17` are decimal 21/22/23), using the existing [extension frame](m1-uart.md).

| OP | Arguments | Effect |
| --- | --- | --- |
| `15` dual.write | A0–1 BE16 number 0..999; A2 format; A3 color 0..3; A4 TTL 0..60 seconds; A5 slot 0..1; A6=0 | Update only this lane; TTL0 invalidates it; does not select a profile/source |
| `16` dual.select | A0=0 original / 1 user; A1..6=0 | Select dual profile and change both lanes with one operation |
| `17` dual.query | A0=slot 0..1; A1..6=0 | Read the lane and global selection without changing profile or renewing leases |

Format/color retain the scalar encodings below. Successful write/select replies contain zero data. Errors use existing statuses without partial mutation. OP `17` returns D0=2, D1=dual global selection, D2=active dual profile AND user selected AND this lane valid, D3=slot, D4–5=number, D6=format, D7=color, D8=remaining TTL rounded up, D9..13=0. D2 does not establish LCD hardware delivery or visibility beneath an expert override.

Both caches, expiry times and selection are MCU RAM; cold boot has no leases and selects original readings. Expert screen overrides take precedence. Lane writes refresh independently; only the global selector is a single operation. Two separate value writes are not an atomic batch. Confirmation requires independent queries of both lanes after writing, matching current configuration, selection, number, format, color and fresh leases. A write ACK is insufficient.

Example: fill both lanes, select user readings together, then independently query each:

```text
23 70 15 01 00 7b 01 03 14 00 00 21
23 70 15 02 01 c8 02 02 0a 01 00 21
23 70 16 03 01 00 00 00 00 00 00 21
23 70 17 04 00 00 00 00 00 00 00 21
23 70 17 05 01 00 00 00 00 00 00 21
```

<a id="display-representation"></a>

### Numbers, units and colors

Each lane has three nonnegative digits: format0 shows `123`, format1 `1.23`, format2 `12.3`; API decimals0/1/2 map to formats0/2/1. Generic lanes have no minus sign or arbitrary text. Wi-Fi encodes `floor(value / scale * 10^decimals + 0.5)`. Values must be finite, nonnegative, within metric bounds, and encode to 0..999; otherwise restore that lane's original reading without clamping, wrapping or fake zero.

Logical units are separate from glass legends. These positions have no selectable W, kW, ℃, %, CO₂ or ppm glyphs. TC1 power hides the original gas/unit; UI must explain its logical unit and scale. Retain a native legend only for slot0+formaldehyde+`mg/m³`+scale1, or slot1+pm25+`µg/m³`+scale1. Scale1000 always hides it, including native metrics. `1230 W / scale1000 / decimals2` shows approximately `1.23`, without a kW glyph.

Colors are off/red/green/yellow. Threshold mode requires `low < high` and compares the unscaled physical value: below low green, at/above low but below high yellow, at/above high red. An explicit API color may override a lease's rule. These colors do not change physical sensor alarms.

### Legacy and dual profiles

Old OP `11`/`12`/`13` retain one scalar cache and their byte layouts. Old `12` selects legacy; new `16` selects dual. Filling caches and all queries never take profile ownership. Under dual, old `13` D1 retains the saved legacy selection and D2 is zero; use new `17` for current dual state. Legacy CO₂ configure still belongs to legacy.

A successful Wi-Fi `display_source.set` persistently selects dual. Successful `co2_source.set` / `co2_display.set` persistently select legacy while retaining dual configuration. Commit profile and related settings in one storage transaction; failure cannot switch profiles. Only the active profile's display scheduler runs.

## Compatible scalar schema 1

Use the [extension frame](m1-uart.md). OP values are hexadecimal:

| OP | Arguments | Effect |
| --- | --- | --- |
| `11` write Wi-Fi value | A0–1 number 0..999; A2 format; A3 color; A4 TTL seconds; A5 slot; A6=0 | Validate and replace cache; does not select the source |
| `12` select source | A0=0 original / 1 Wi-Fi; A1–6=0 | Select one of exactly two sources |
| `13` query | A0–6=0 | Return selection, effective validity, cache and remaining TTL |

A2 bits 0..1 select decimal point: 0 none, 1 after left digit, 2 after middle digit, 3 invalid. Bit2 keeps the slot's original gas/unit legend; zero hides it. Bits3..7 are zero. A3 color: 0 off, 1 red, 2 green, 3 yellow. A4 TTL: 0 invalidates, 1..60 grants seconds. A5 slot: 0 HCHO, 1 PM.

Units can only select legends physically present on the glass. There is no CO₂/ppm legend. CO₂ mode hides the original gas/unit and does not invent an icon.

OP `13` returns D0=schema 1, D1=selected source, D2=Wi-Fi selected and cache valid, D3=slot, D4–5=number, D6=format, D7=color, D8=remaining TTL rounded up to seconds, D9–13=0. D2 is not a hardware readback and does not account for a higher-priority expert screen override.

Expiry returns to original readings even while Wi-Fi remains selected. Fresh renewal can restore Wi-Fi output. Do not send fake zero for invalid data. Expert screen overrides take precedence; existing OTA/reset exclusion still applies. Settings and leases are RAM-only; Wi-Fi MCU resynchronizes after reboot.

Example: 1234 ppm, HCHO slot, yellow, 20-second lease. Wi-Fi converts this to digits 123 and a decimal point after the left digit:

```text
23 70 11 01 00 7b 01 03 14 00 00 21
23 70 12 02 01 00 00 00 00 00 00 21
23 70 13 03 00 00 00 00 00 00 00 21
```

Current Wi-Fi CO₂ policy: 1..999 is integer; 1000..9999 uses truncated `ppm/10`, showing `1.00`..`9.99`; 10000..65535 uses truncated `ppm/100`, showing `10.0`..`65.5`. Below the low threshold is green, at/above low but below high is yellow, at/above high is red. Wi-Fi computes alternation and manual toggling; the display MCU needs no CO₂ policy.

## Button event schema 1

After capability D9=1, parse this independent 20-byte event:

```text
23 71 01 KIND SEQ HELD_HI HELD_LO 00 00 00 00 00 00 00 00 00 00 00 00 21
```

Kinds: 1 single click, 2 double click, 3 approximately 3-second hold, 4 10-second hold. SEQ advances per event and wraps at 8 bits; zero is valid. It supports adjacent duplicate filtering. HELD is big-endian milliseconds, capped at 65535; current single-click events use zero and double-click events report the second press duration.

Debounce is 20 ms; a short press lasts 60..2999 ms. A first short release waits over 350 ms for a single click. Completing a second qualifying short press within the window emits a double click without legacy `0x0f`. Single clicks retain `0x0f`. Reaching 3 seconds emits only KIND=3 and legacy `0x04` notifications; releasing after at least 3 but less than 10 seconds requests reprovisioning. Holding continuously for 10 seconds emits KIND=4 and immediately requests a factory reset, without waiting for release. The new gesture flow never automatically sends legacy reprovision `0x18` or display test `0x10`; explicit debug commands may still invoke the latter. OTA/reset wait clears pending clicks.

Wi-Fi double-click priority:

1. Cancel a ringing alarm and do not toggle the display.
2. Otherwise, when `switch_display` and the active profile/capabilities permit it, dual profile toggles both lanes together between original/user readings; legacy profile retains its CO₂ behavior.
3. Otherwise do nothing custom. Expiry restores original readings; OTA, reset or configuration busy excludes custom actions.

## Button reset transaction m1-reset-v1

`m1-reset-v1` uses the independent command `0x72`. It is neither a `0x70` sub-operation nor the OTA command `0x16`. Sensor MCU requests are 20 bytes; Wi-Fi MCU ACKs are 12 bytes:

```text
23 72 01 KIND SEQ 00 00 00 00 00 00 00 00 00 00 00 00 00 00 21
23 72 01 KIND SEQ 00 00 00 00 00 00 21
```

Here KIND=1 means reprovision and 2 means factory reset, independently of button-event `0x71` kinds. Reserved bytes must be zero. Each new transaction advances an 8-bit SEQ, including wrap to zero. Retry the same KIND/SEQ every 500 ms for at most 5 seconds. OTA, a pending reset or a committed reset excludes another physical-button transaction.

After validating the complete request, Wi-Fi calls `m1_reset(kind == 2)` and sends the matching KIND/SEQ ACK only after persistence succeeds. Busy or failed persistence produces no ACK or committed receipt, allowing a later retry. A duplicate committed transaction receives another ACK without another Flash write. Ignore conflicting transactions without escalating to factory reset.

Sensor MCU accepts an ACK only for its local pending transaction, with matching schema, KIND, SEQ and reserved bytes, within the 5-second window; elapsed time of 5000 ms is already expired. Orphan, late or incorrect ACKs cannot reset it. On confirmation, hold Wi-Fi EN low for at least 1 second, then reset the sensor MCU; startup raises Wi-Fi EN again. Without a valid ACK, do not cut Wi-Fi power. After timeout, release and hold again to start a new transaction.

Both MCUs require matching updates. Old Wi-Fi ignores `0x72`; new sensor firmware does not fall back to `0x18` or downgrade factory reset to reprovisioning. New Wi-Fi still accepts legacy sensor `0x18`, persists its original partial reset, then sends the old fixed `0x16` magic ACK. Existing OTA `0x16` retains its 4-second commit delay followed by at least 1 second with Wi-Fi EN low.

Factory reset retains the scope of Wi-Fi `m1_reset(true)`: restore all `app_storage` defaults and restart the sensor MCU to clear RAM state. Independent Flash RTTTL music remains. See the [reset contract](contracts/m1-reset-v1.json) and [positive/negative transaction vectors](contracts/vectors/m1-reset-v1.json).
