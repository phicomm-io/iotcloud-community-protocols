# M1 display sources and buttons

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/m1-display/)

Dual-lane contract `m1-display-v2` uses the independent capability and additive operations in `m1-uart-v3`. Existing scalar schema 1 keeps its meaning. This development extension records implementation, builds and physical acceptance separately; publishing documentation does not establish device acceptance.

## Dual-lane schema 2

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

Colors are off/red/green/yellow. Threshold mode requires low<high and compares the unscaled physical value: below low green, at/above low but below high yellow, at/above high red. An explicit API color may override a lease's rule. These colors do not change physical sensor alarms.

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
