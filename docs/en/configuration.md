# Backups, language and updates

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/configuration/)

## Full backups

When a v1 device declares `config_backup:1`, use password-protected LAN HTTP for full backups. Files contain Wi-Fi and MQTT credentials. v0.9.x public configuration exports are partial backups and cannot be restored as full snapshots. M1 sensor MCU music is separate from Wi-Fi configuration.

MiCO devices (TC1/A1/M1) use a 104-byte header and a model-specific native payload, at most 16384 bytes in total:

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 8 | ASCII `PHCBACK1` |
| 8 | 8 | NUL-terminated model |
| 16 | 40 | NUL-terminated variant |
| 56 | 32 | NUL-terminated firmware version |
| 88 | 4 | Schema, currently 1 |
| 92 | 4 | Storage revision |
| 96 | 4 | Payload length |
| 100 | 4 | Payload CRC-32, reflected polynomial `0xedb88320`, initial/final XOR `0xffffffff` |

32-bit integers are little-endian. Require exact model, variant, storage revision, length and CRC, then validate payload semantics. The payload is a storage-specific native snapshot, not portable serialization.

DAIKIN uses a separate JSON envelope with `schema`, `model`, `variant`, `firmware`, `config_version`, `config`. MiCO files and DAIKIN `full` / future `hub` files are not interchangeable. Validate the entire candidate before a single persistence operation; preserve old settings on failure.

## Recovery mode

`config.get.migration_state` is `ready` or `confirmation_required`. The latter means recoverable provisioning is using RAM defaults while original storage awaits user action. Show explicit confirmation before clearing. Ordinary settings and background tasks must not overwrite original Flash in recovery mode.

## Language

Device `config.get.language` is `zh-CN` or `en`, defaulting to `zh-CN`. Persist it through `config.set` in `values.language`:

```json
{"request_id":"language_1","action":"config.set","params":{"values":{"language":"en"}}}
```

Browser language is separate and can follow automatic or manual selection. Device language selects MQTT Discovery names; republish names after changes while preserving unique IDs, topics and usernames. Full backups retain the device language.

## OTA routing and dependencies

The v1 development route is `/ota/v1/<model>/<variant>/latest.json`. After formal acceptance of the bridge release, legacy routes stop at v1.0.0 instead of offering future incompatible releases to v0.9.x devices. Routing promotion is a separate release operation.

Select OTA by model, variant, signature and version. DAIKIN `hub` is a separate variant; ordinary `full` devices do not automatically cross-upgrade. The browser fetches and verifies release differences directly; when unavailable, explain the failure and require additional confirmation.

Record Wi-Fi firmware, sensor MCU and frontend versions independently. Firmware consumes a full-commit, SHA-256-pinned frontend release. A successful build or UART transfer does not prove the new application is running.
