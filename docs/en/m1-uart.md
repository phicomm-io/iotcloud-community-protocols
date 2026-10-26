# M1 UART and capabilities

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/m1-uart/)

Wi-Fi and sensor MCU communicate over SERCOM3 UART, 115200 8N1. Ordinary requests are 12 bytes; replies/events are 20 bytes, beginning `23` and ending `21`. There is no separate checksum byte. Multibyte values are big-endian. OTA blocks have a separate variable-length format.

[Button reset `0x72`](m1-display.md#button-reset-transaction-m1-reset-v1) has an independent 20-byte sensor request / 12-byte Wi-Fi ACK and requires matching implementations in both firmwares.

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
| D12 / f17 | Optional sensor-buzzer schema; 1 supports OP `14`, 0 means absent |
| D13 / f18 | `m1-uart-v3` dual display schema; 2 supports OP `15`–`17`, 0 unavailable; old v2 requires zero |

Factory MCU does not implement `0x70`. New capabilities use D9..D13 without changing the old bitmap or D0=2. Disable an extension when its capability is absent. The new schema is a development implementation; the Wi-Fi firmware version alone does not establish that the sensor MCU was upgraded.

Contract revision is separate from the frame protocol number. Old `m1-uart-v2` keeps its [v1 artifact](contracts/m1-uart-v1.json) and [original vectors](contracts/vectors/m1-uart-v1.json), including D13=0. The additive [v3 artifact](contracts/m1-uart-v3.json) and [v3 vectors](contracts/vectors/m1-uart-v3.json) declare D13=2 and dual operations, allowing zero to represent absent support. Consumers explicitly select the new contract and update their pins; nonzero D13 does not satisfy the old fixed-zero contract. Old Wi-Fi clients ignoring the new field still use scalar operations.

## Operation groups

| Group | OP | Purpose |
| --- | --- | --- |
| Product features | `09`, `0b`, `0e`, `0f`, `11`, `12`, `14`–`16` | Thresholds, tones/music, scalar/dual writes and selection, optional sensor buzzer |
| Compatibility | `0a`, `0c`, `0d` | Existing CO₂ config, reading and status; new v1 clients use generic display |
| Read-only diagnostics | `00`, `06`, `08`, `10`, `13`, `17` | Capabilities, health, display cache, raw sensor frames, scalar/dual state |
| Expert tools | `01`–`05`, `07` | PWM, screen/numeric/segment overrides, exit, PM mode |

Existing opcodes remain assigned. See [MCU implementation docs](https://github.com/phicomm-io/phicomm_m1_mcu_atsamd20/tree/main/docs) for existing music/update details. Shared new display and button definitions are on the [next page](m1-display.md).

## OP `14`: optional sensor buzzer

OP `14` means hexadecimal `0x14`, decimal 20. First verify that OP `00` D12 equals 1. It controls sensor threshold reminders only; wake alarms, music and explicit buzzer commands remain independently controlled.

| Byte | Request |
| --- | --- |
| A0 | 0: read; 1: replace the entire enable mask |
| A1 | Write mask: bit0 HCHO, bit1 PM2.5, bit2 legacy CO₂; bits3..7 must be zero. Must be zero on read |
| A2..A6 | Must be zero |

In a successful reply STATUS is at f4; D0 is schema 1, D1 is the MCU's actual enable mask (0..7), D2 is `alarm_latched` from the latest runtime poll (0/1), and D3..D13 are zero. Invalid arguments return STATUS 1; OTA busy returns STATUS 2. `alarm_latched` represents an enabled, healthy sensor exceeding its red threshold. It is not sound sensing and does not establish that the buzzer is currently sounding.

The MCU keeps its mask in RAM only and cold-starts at 0: all reminders default off. Wi-Fi persists the desired HCHO and PM2.5 switches (mask 0..3), writes after capability negotiation, then verifies with a separate read request. The write reply does not establish readback confirmation. A readback must match the current configuration revision and remain fresh. Poll every 5 seconds after confirmation; after 15 seconds without fresh readback, actual state is unknown. Old MCUs may save desired settings but must receive no undeclared OP `14` and must not be reported as physically silenced. [`alarm.get/set`](device-http.md#m1-sensor-reminders) reports desired and actual state separately.

## Stable PM2.5 readings and raw diagnostics

The development implementation keeps a 3-second sampling interval. It takes the median of the latest three valid readings, then applies a Q8 EMA for ordinary display/telemetry. The first valid sample seeds the filter. An upward difference of at least 20 µg/m³ uses 75% of the new value; a smaller rise uses 50%; a fall uses 25%. This rejects an isolated excursion while allowing sustained rises to reach the display promptly. Filter state occupies 12 bytes and changes neither UART frame length, the old capability bitmap nor raw sensor bytes.

Error frames never inject zero into the filter. Three consecutive errors, or more than 6000 ms since the last healthy sample, invalidate health and restart warming. An invalid reading must not be published as valid zero concentration. OP `10` raw sensor diagnostics preserve received sensor frames, including error frames and rejected excursions. The smoothed display value must not replace these raw bytes.

Diagnostic flags remain `PRESENT=0x01`, `CHECKED=0x02`, `ERROR=0x04`, `WARMING=0x08`, `FILTERED=0x10`. Set `FILTERED` only when the raw value differs from the median by at least 20 and by more than 50% of the median: a large raw excursion has not yet been confirmed by the median. Ordinary EMA smoothing does not set the flag. Raw values, smoothed readings, health/warming and this flag carry distinct information.

Implementation: `mcu/src/{debug,runtime,pm_filter}.c`, `mcu/tests/{test_core,test_runtime,test_pm_filter}.c`, `firmware/M1/mcu.c`. See [machine contracts](contracts.md) for repository aliases and commit pins. Source and host-test evidence does not establish a published v1 release or physical-device acceptance.
