# Schemas and examples

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/contracts/)

Review machine-readable artifacts with the prose. Reuse them in firmware host tests, frontend and platform tests. Passing checks establishes the covered contract behavior, not physical-device acceptance.

| File | Contents |
| --- | --- |
| [Interface registry](contracts/registry.json) | Interface IDs, versions, status, producers/consumers and implementation paths |
| [CO₂ sensor Schema](contracts/schemas/sensor-co2-v1.schema.json) | CO₂ ingress fields for account-scoped sensor messages |
| [Source configuration Schema](contracts/schemas/m1-co2-source-set-v1.schema.json) | Strict `co2_source.set` parameters |
| [Sensor reminder write](contracts/schemas/m1-alarm-set-v1.schema.json) / [state](contracts/schemas/m1-alarm-state-v1.schema.json) | Optional buzzer switches, desired/actual readback and unknown state on old MCUs |
| [Hub rules](contracts/daikin-hub-v1.json) | Authentication, ports, route origins, freshness and HAP storage boundaries |
| [Local account Schema](contracts/schemas/hub-setup-v1.schema.json) | Initial local owner setup |
| [Upstream route Schema](contracts/schemas/hub-bridge-set-v1.schema.json) / [Bemfa Schema](contracts/schemas/hub-bemfa-set-v1.schema.json) | Explicit direction, retained restrictions and model/channel mappings |
| [HAP settings](contracts/schemas/hub-homekit-set-v1.schema.json) / [pairing erase](contracts/schemas/hub-homekit-reset-v1.schema.json) / [state](contracts/schemas/hub-homekit-state-v1.schema.json) | Strict writes, explicit erase confirmation and pairing credential visibility |
| [Dual configuration](contracts/schemas/m1-display-source-set-v2.schema.json) / [runtime](contracts/schemas/m1-display-source-state-v2.schema.json) / [API lease](contracts/schemas/m1-display-data-set-v2.schema.json) | Independent lanes, global selection, CAS, explicit clear and MCU confirmation boundaries |
| [Generic typed sensors](contracts/schemas/sensor-values-v1.schema.json) | Same-account measurements, TC1 power, A1 main-fan percentage, exact units and invalid null |
| [Dual UART v3](contracts/m1-uart-v3.json) / [new vectors](contracts/vectors/m1-uart-v3.json) | D13 schema2, additive21/22/23 and scalar compatibility; original v1 files retained |
| [Button reset](contracts/m1-reset-v1.json) / [transaction vectors](contracts/vectors/m1-reset-v1.json) | Independent `0x72` frames, pending ACK matching, retry after failed persistence, deduplication and conflict protection |
| [Positive/negative JSON examples](contracts/examples/cases.json) | Type, range, unit, unknown-field and embedded-NUL boundaries |
| [MCU capabilities and operations](contracts/m1-uart-v1.json) | Frame sizes, status values, capability offsets, display and sensor-buzzer operations |
| [UART vectors](contracts/vectors/m1-uart-v1.json) | Display, buttons, OP `14` requests/replies and capability compatibility |

From the repository root:

```sh
python tools/validate.py
python tools/build.py
python tools/validate.py --consumer /path/to/implementation
python tools/validate.py --sources /path/to/workspace
```

The registry's `repositories` maps `firmware`, `mcu`, `frontend` and `platform` to Git repositories. Each `implementation` / `verification` reference is a real file path following that alias. `--sources` checks those paths in a workspace with matching directory names. Before consumer validation, check out the full specification commit in `protocols.lock.json` and verify the registry SHA-256. Record the implementation commit and any dirty patch digest separately. Development source paths do not establish a public release.

Schemas constrain structure and expressible field relationships. Firmware measures string limits in UTF-8 bytes; JSON Schema measures characters, so ingress must also check UTF-8 and byte lengths. Runtime checks establish `yellow <= red`, topic/ID agreement, owner authorization, unique route/channel keys, empty-key preservation, freshness, sequence replay, desired/actual mask agreement, persistence rollback and UART scheduling. Two schema-valid messages may still conflict because of a repeated sequence. The UART validator interprets declared fields and conditions instead of copying MCU control logic.

Dual threshold objects declare `x-orderedFields:["low","high"]` for strict low<high. This repository validator implements that relation beyond standard JSON Schema; consumers using only a generic validator must check it separately. Configuration revisions, source/unit matching, API TTL bounded by configuration, scaled representability and readback confirmation remain runtime checks. UART v3 validation runs both original/new vectors and verifies that existing layouts and fields were not redefined.

Button-reset vectors check framing, schema, reserved bytes, pending transaction matching, the 5-second ACK boundary and the persistence/deduplication model. Consumers must still test actual button timing, 500 ms retries, Flash commits, Wi-Fi EN low for at least 1 second and both MCU restarts. Passing contract checks does not establish hardware acceptance.
