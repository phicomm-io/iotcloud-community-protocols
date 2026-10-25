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

<a id="m1-display-storage-v9"></a>

## M1 dual display storagev9

Append dual configuration after the v8 payload without moving its prefix or CO₂ fields. Migrating v8 preserves ordinary settings, legacy CO₂, thresholds, buzzer choices, automation and revisions. Keep legacy profile active; new lanes default to none without RAM leases. Only explicit new SET enables dual.

A full v8 backup is an explicit compatibility exception: validate original model/variant, exact v8 length, CRC and legacy semantics before bounded migration into v9 with an initialized tail. V9 backups still require exact v9 length and semantics; reject unknown future versions. Persist profile/settings together and interpret the result using the commit boundaries below. Leased API values and remaining lifetimes are excluded from backups.

<a id="storage-commit-results"></a>

## MiCO storage commit results

These rules apply to TC1 / A1 / M1 development implementations with the transactional storage fix. CAS conflicts or `busy` reject the candidate before writing. For an update from a valid stored configuration, if the candidate is confirmed uncommitted, `storage_error` restores the old RAM configuration and preserves at least one valid copy of the old configuration.

Once the complete primary contents and its CRC commit record are confirmed, the configuration is committed: return `accepted` and retain the new RAM configuration. A failure refreshing the secondary copy leaves the result accepted. Acceptance does not guarantee that both copies are healthy.

Persistent read failures after writing the commit record can leave the result indeterminate. Return the existing `storage_error` and restore old RAM settings, but Flash may contain the old or new configuration. Lock further writes for this boot, enter read-only recovery with `migration_state=confirmation_required`, and preserve readable copies. Ordinary GET reads RAM and cannot prove Flash rollback. After reboot successfully completes configuration reads and any required copy repair, independently GET and compare revision and full configuration. This adds no error code or automatic rewrite of old settings.

## Recovery mode

`config.get.migration_state` is `ready` or `confirmation_required`. The latter indicates configuration recovery: provisioning may use RAM defaults, or an indeterminate commit may preserve old RAM settings as described above. Clearing original storage still requires explicit confirmation. Ordinary settings and background tasks must not overwrite original Flash in recovery mode.

## Language

Device `config.get.language` is `zh-CN` or `en`, defaulting to `zh-CN`. Persist it through `config.set` in `values.language`:

```json
{"request_id":"language_1","action":"config.set","params":{"values":{"language":"en"}}}
```

Browser language is separate and can follow automatic or manual selection. Device language selects MQTT Discovery names; republish names after changes while preserving unique IDs, topics and usernames. Full backups retain the device language.

## OTA routing and dependencies

The v1 development route is `/ota/v1/<model>/<variant>/latest.json`. After formal acceptance of the bridge release, legacy routes stop at v1.0.0 instead of offering future incompatible releases to v0.9.x devices. Routing promotion is a separate release operation.

Select OTA by model, variant, signature and version. DAIKIN `hub` is a separate variant; ordinary `full` devices do not automatically cross-upgrade. The browser fetches and verifies release differences directly; when unavailable, explain the failure and require additional confirmation.

DAIKIN `full` development firmware declaring `ota_variant_conversion:"full-to-hub"` may use the dedicated [explicit signed conversion endpoint](device-http.md#explicit-daikin-full-hub-conversion). Ordinary signed/unsigned OTA preserves the variant. Conversion does not alter the partition table and does not support `hub` → `full`.

Record Wi-Fi firmware, sensor MCU and frontend versions independently. Firmware consumes a full-commit, SHA-256-pinned frontend release. A successful build or UART transfer does not prove the new application is running.
