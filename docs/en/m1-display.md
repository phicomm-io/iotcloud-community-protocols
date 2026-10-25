# M1 display sources and buttons

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/m1-display/)

Requires generic display schema 1. Wi-Fi MCU owns source selection, numeric conversion, units, color thresholds and alternation timing. Sensor MCU owns physical rendering and two display sources, defaulting to original sensor readings. Overrides do not replace HCHO/PM measurements, queries or alarms.

## Generic display API

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

Debounce is 20 ms; a short press lasts 60..2999 ms. A first short release waits over 350 ms for a single click. Completing a second qualifying short press within the window emits a double click without legacy `0x0f`. Single clicks retain `0x0f`; holds retain `0x04` / `0x10`, with the existing release-to-provision behavior. OTA/reset wait clears pending clicks.

Wi-Fi double-click priority:

1. Cancel a ringing alarm and do not toggle the display.
2. Otherwise, when `switch_display` is configured, a local/external CO₂ source is configured, and capabilities permit it, toggle only original / Wi-Fi sources.
3. Otherwise do nothing custom. Expiry restores original readings; OTA, reset or configuration busy excludes custom actions.
