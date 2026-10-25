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
