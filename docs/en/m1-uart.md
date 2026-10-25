# M1 UART and capabilities

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/m1-uart/)

Wi-Fi and sensor MCU communicate over SERCOM3 UART, 115200 8N1. Ordinary requests are 12 bytes; replies/events are 20 bytes, beginning `23` and ending `21`. There is no separate checksum byte. Multibyte values are big-endian. OTA blocks have a separate variable-length format.

## Versions and extension frames

Ordinary command `0x11` queries the sensor MCU version. Reply f2 is the length; f3 starts the raw string, at most 16 bytes. Show Wi-Fi firmware separately. Factory `11.x` users are the initial target for open-source MCU firmware; factory `17.1.2.3` / `17.x` awaits the corresponding image and compatibility analysis. Show unknown versions as unknown.

Extension request:

```text
23 70 OP SEQ A0 A1 A2 A3 A4 A5 A6 21
```

Reply:

```text
23 70 OP SEQ STATUS D0 D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D13 21
```

SEQ is 0..255. Reserved arguments and unused reply bytes must be zero. Route ordinary readings, clock and event frames independently; do not assume the next frame answers the pending request.

| STATUS | Meaning |
| --- | --- |
| 0 | Accepted / query succeeded |
| 1 | Invalid arguments |
| 2 | OTA reception busy |
| 3 | Unsupported |
| 4 | Peripheral configuration failed |
| 5 | Sensor cache generation changed; read again |

Success means the runtime accepted the request. Rendering and hardware output occur later. Reusing SEQ re-executes the operation. No new commands are accepted while a committed update awaits reset.

## OP `00` capabilities

Arguments are zero. D0 begins at absolute frame offset 5:

| Data / frame offset | Meaning |
| --- | --- |
| D0 / f5 | Extension protocol version, currently 2 |
| D1–2 / f6–7 | Bitmap for OP `00`–`0f`, currently `ffff` |
| D3–4 / f8–9 | Maximum expert override lease, 10000 ms |
| D5 / f10 | Hardware PWM callback exists |
| D6–8 / f11–13 | Sensor-frame schema, kind count, maximum chunk |
| D9 / f14 | Button event schema; 1 supports extended events |
| D10 / f15 | Button kind bits 0..3 correspond to kinds 1..4; currently `0f` |
| D11 / f16 | Generic display schema; 1 supports OP `11`–`13` |
| D12–13 / f17–18 | Reserved zero |

Factory MCU does not implement `0x70`. New capabilities use D9..D11 without changing the old bitmap. Disable an extension when its capability is absent.

## Operation groups

| Group | OP | Purpose |
| --- | --- | --- |
| Product features | `09`, `0b`, `0e`, `0f`, `11`–`13` | Thresholds, tones/music, generic display |
| Compatibility | `0a`, `0c`, `0d` | Existing CO₂ config, reading and status; new v1 clients use generic display |
| Read-only diagnostics | `00`, `06`, `08`, `10` | Capabilities, health, display cache, raw sensor frames |
| Expert tools | `01`–`05`, `07` | PWM, screen/numeric/segment overrides, exit, PM mode |

Existing opcodes remain assigned. See [MCU implementation docs](https://github.com/phicomm-io/phicomm_m1_mcu_atsamd20/tree/main/docs) for existing music/update details. Shared new display and button definitions are on the [next page](m1-display.md).
