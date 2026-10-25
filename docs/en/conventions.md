# Evolution and coordination

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/conventions/)

Agree on interfaces and failure handling here first. MCU, firmware, frontend and platform implementation PRs reference the same specification commit.

## Versions and capabilities

- Specification version, HTTP path version, MQTT protocol version, JSON schema, storage revision and firmware version are independent.
- Negotiate features through capabilities, supported actions and MCU capability fields. Follow response extension rules when ignoring unknown fields; never report an unknown action as successful.
- Keep assigned field, topic and opcode meanings. Breaking changes need a new schema or path, plus migration or explicit rejection.
- Validate the complete configuration write. Reject unknown fields, wrong types, embedded NUL and out-of-range values. Strings, numbers and booleans are distinct JSON types.
- Preserve factory MCU version strings. Factory `11.x`, `17.x` and open-source MCU versions are different families and must not be ordered as one semantic version series.

## Data and failures

Define whether a time value means UTC, device uptime or sample age. For remote sensors, add elapsed local time after receipt to `age_ms`; never compare uptime from two devices. Use unsigned elapsed-time arithmetic across counter wrap, with validity windows below half the counter range.

Do not convert invalid, expired or offline measurements into zero. Expose validity and omit unavailable readings. An expired display override returns to physical sensor readings. `accepted` means a request was accepted; persistence, physical output and completed reboot require separate verification.

MQTT retries reuse the original `request_id` and content. A new ID may execute again. UART `0x70` SEQ matches a reply and provides no deduplication; a retry can restart a lease or music operation.

## Configuration compatibility

Complete migration and validation in RAM, then persist once. Preserve existing Wi-Fi, MQTT, name and product settings. On failure, retain the original Flash and enter recoverable provisioning. Unknown future storage revisions must not be overwritten silently; clearing requires explicit user confirmation.

Restore requires matching model, variant, schema, storage revision and length. Full backups contain credentials and require password-protected LAN HTTP; do not forward them through MQTT or iframe messages. M1 MCU music is backed up separately.

## Delivery and pins

Consumers use `protocols.lock.json` to pin a full specification commit and the SHA-256 of `contracts/registry.json`. Firmware still uses `frontend.lock.json` for an immutable frontend artifact; a protocol pin does not replace that artifact lock.

Update both languages, schemas, positive/negative examples and implementation references together. Automated checks cover format and boundaries. Physical display, buttons, recovery and resource budgets need the corresponding hardware evidence. Working branches, documentation publication and firmware releases are independent.
