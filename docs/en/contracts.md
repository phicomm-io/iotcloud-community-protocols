# Schemas and examples

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/contracts/)

Review machine-readable artifacts with the prose. Reuse them in firmware host tests, frontend and platform tests. Passing checks establishes the covered contract behavior, not physical-device acceptance.

| File | Contents |
| --- | --- |
| [Interface registry](contracts/registry.json) | Interface IDs, versions, status, producers/consumers and implementation paths |
| [CO₂ sensor Schema](contracts/schemas/sensor-co2-v1.schema.json) | CO₂ ingress fields for account-scoped sensor messages |
| [Source configuration Schema](contracts/schemas/m1-co2-source-set-v1.schema.json) | Strict `co2_source.set` parameters |
| [Positive/negative JSON examples](contracts/examples/cases.json) | Type, range, unit, unknown-field and embedded-NUL boundaries |
| [MCU capabilities and operations](contracts/m1-uart-v1.json) | Frame sizes, status values, capability offsets and generic display operations |
| [UART vectors](contracts/vectors/m1-uart-v1.json) | Display requests, queries and button events |

From the repository root:

```sh
python tools/validate.py
python tools/build.py
python tools/validate.py --consumer /path/to/implementation
```

Check out the commit specified by a consumer's `protocols.lock.json` before consumer validation. Schemas cannot establish account authorization, topic/ID agreement, freshness, sequence replay, persistence rollback or UART scheduling. Two schema-valid messages may still conflict because of a repeated sequence.
