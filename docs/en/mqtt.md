# MQTT and sensors

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/mqtt/)

TMCP (Tom MQTT Cloud Protocol) uses `protocol:"tmcp"`, `protocol_version:2`, `version:"v2"`. Normalize a MAC to 12 lowercase hex digits. Account scope is `u_` followed by the hex encoding of the MQTT username's UTF-8 bytes; a Broker with no username uses `local`.

<a id="sensor-values-v2"></a>

## Generic device fields: sensor-values-v2

The RC.1 implementation targets wire **schema2**. `sensor-values-v1` / schema1 from the old v1.0.0-rc are **deprecated**; RC.1 does not promise old-RC feed compatibility. This protocol is implemented but the revised RC.1 release is not yet public. The topic remains `phicomm/v2/<scope>/sensor/<device_id>/state`, non-retained, under the authenticated account. Device model never chooses accepted fields.

```json
{"schema":2,"device_id":"001122334455","model":"custom_meter","boot":123,"sequence":7,"sensors":{"load":{"name":"Load","type":"number","unit":"widgets/s","value":12.5,"valid":true,"age_ms":0},"future":{"name":"Future status","type":"string","unit":"","value":"ready","valid":true,"age_ms":0}}}
```

| Field | Contract |
| --- | --- |
| `schema` | Integer 2; old schema1 is not reinterpreted |
| `device_id` | Canonical lower-case 12-hex identity, equal to the topic identity |
| `boot`, `sequence` | Integers 1..4294967295; boot identity and monotonically advancing sequence provide live replay protection, not wall-clock timestamps |
| `model` | Optional informational name, 1..32 UTF-8 bytes; no model whitelist or source binding |
| `sensors` | Object containing 1..16 fields, keyed by stable `field_id`: ASCII `[a-z][a-z0-9_]{0,31}` |
| `name` | Required display label, 1..64 UTF-8 bytes; changing a label does not change field identity |
| `type` | Required 1..16 ASCII token `[a-z][a-z0-9_]{0,15}`; only `number` is currently consumed |
| `unit` | Required 0..24 UTF-8 bytes, including empty; metadata from the publisher, not inferred from model or field name |
| `valid`, `value` | Boolean validity. `valid=false` requires `value:null`; a valid `number` requires a finite JSON number whose float32 conversion remains finite. Booleans, numeric strings and non-finite/overflow numbers are not numbers; signed values are allowed |
| `age_ms` | Required integer 0..4294967295. A valid field must have age below 20000 ms; invalid fields may report greater age |

Names/units must be valid UTF-8 without unpaired surrogates, ASCII C0 controls U+0000..U+001F or DEL U+007F. Byte limits are independent of character counts. Envelope and descriptor response extensions are additive; configuration writes remain strict. A descriptor accompanies every live value, avoiding a separate stale discovery cache or descriptor/value revision race. Publishers choose stable field IDs and accurate names/units for their real measurements or applied outputs; current TC1 power and A1 effective fan percentage are examples, not a whitelist. Field descriptors do not turn a requested setting into a measured value.

Consumers first check account/topic identity, non-retained live delivery, boot/sequence and freshness. Then handle each field independently: unknown types are future extension envelopes and may carry arbitrary JSON values, but current M1/frontend must **ignore their values** without numeric conversion or synthetic zero. Each accepted new boot/sequence is a **complete snapshot**: missing, unsupported typed, malformed or invalid fields immediately revoke the previous numeric candidate; they never renew a valid numeric lease. Retain the configured source binding and record the accepted boot/sequence even when all numeric fields disappear, preventing old numeric replay from restoring them. A bad or unsupported field must not prevent a valid numeric sibling from being used. A schema-invalid envelope is not proof of a valid sample. Same-boot duplicate/out-of-order sequence numbers, unauthorized identities, retained frames and offline/stale producers cannot renew leases.

M1 MQTT sources bind `device_id + field_id + expected type + expected unit`, not `model` or `name`. Only `type:number` is selectable now. A recognized sample with invalid data or a mismatching expected unit cannot drive that lane. Missing/unsupported fields or a changed unit immediately invalidate the old numeric candidate in a newly accepted complete snapshot; the affected lane falls back without deleting its configuration. Renaming `name` only changes the label. Original source age plus local elapsed time must stay below both the feed 20 s limit and configured lane TTL. Negative numbers can be valid feed values while M1's nonnegative glass format returns `out_of_range`. Unit strings are metadata: the fixed glass does not gain new symbols. See [profile4](device-http.md#m1-generic-profile4).

[Normative contract](contracts/sensor-values-v2.json) · [Schema](contracts/schemas/sensor-values-v2.schema.json) · [Positive/negative examples](contracts/examples/sensor-values-v2.json). `x-utf8Bytes` and `x-float32Finite` are enforced by this repository validator; generic JSON Schema tools must implement equivalent runtime checks.


## Device topics

Device root: `phicomm/v2/<scope>/<model>/<mac>`. Models include `tc1`, `m1`, `a1`, `daikin`, according to discovery.

| Topic or suffix | Retain | Payload |
| --- | --- | --- |
| `phicomm/v2/<scope>/discovery/<mac>` | Yes | schema 1, model and full TMCP protocol markers |
| `<root>/availability` | Yes / LWT | `online` / `offline` |
| `<root>/state` | Yes | Device snapshot |
| `<root>/capabilities` | Yes | Supported actions and metadata |
| `<root>/command` | No | [Command envelope](device-http.md) |
| `<root>/result` | No | Reply with the same `request_id` |

Broker ACLs derive account ownership from authenticated connections and topic namespaces, not user fields in payloads. Only explicitly authorized devices are accessible. The same MAC can exist in separate accounts; it is not a globally unique platform key. Reject retained commands.

Home Assistant discovery uses `homeassistant/<component>/<scope>/<model>_<mac>_<entity>/config`. Generic discovery subscriptions still require per-message account checks and grant no cross-account read or wildcard publishing. Changing language updates names while preserving entity IDs, topics and account keys.

## Cross-device sensor schema 1

Topic: `phicomm/v2/<scope>/sensor/<device_id>/state`. Providers report physical measurements. A consumer must not republish display-forwarded values as its own physical sensor.

```json
{"schema":1,"device_id":"123456abcdef","boot":123,"sequence":1,"sensors":{"co2":{"valid":true,"value":1234,"unit":"ppm","age_ms":0}}}
```

| Field | Rule |
| --- | --- |
| `schema` | Integer 1 |
| `device_id` | Must match the lowercase ID in the topic |
| `boot`, `sequence` | Integers 1..4294967295; boot identifies a startup, sequence advances within it |
| `sensors.co2.valid` | JSON boolean |
| `value`, `unit` | Valid CO₂ is finite, 1..65535, with exact unit `ppm` |
| `age_ms` | Nonnegative integer sample age at transmission; add local elapsed time after receipt |

Other sensor fields may include `temperature` (`°C`), `humidity` (`%`), `pm25` (`µg/m³`) and `formaldehyde` (`mg/m³`). The provided Schema validates the CO₂ ingress profile; it does not validate those fields' separate units and ranges.

M1 accepts only live messages from the configured source in its account. Ignore retained replay, mismatching IDs, duplicate/out-of-order sequence values and recently retired boot IDs. The bounded retired-boot cache is held in RAM and does not replace Broker authentication or ACLs. A newer message with invalid CO₂ invalidates the previous reading immediately. When `age_ms + elapsed >= 20000`, stop renewing the display lease. A new MQTT session clears the remote cache until fresh data arrives.

Some existing implementations also expose flat sensor fields. New v1 integrations should use the `sensors` structure. A retained online snapshot cannot prove sample freshness.

<a id="sensor-values-v1"></a>

## Generic typed feed: sensor-values-v1

Additive profile `sensor-values-v1` uses the same account-scoped topic and wire schema1, defining multiple optional physical quantities without changing `sensor-co2-v1` or putting power in CO₂ fields. Messages are non-retained; retained device snapshots cannot replace this feed. `device_id` must match the topic, not an `id` field. Optional `model` is one of m1/daikin/tc1/a1 and grants no cross-account access. When present, known metrics must match its producer subset: M1 climate/PM2.5/HCHO/CO₂/pressure; DAIKIN also PM10/TVOC; TC1 power/energy; A1 fan_speed_percent. Unknown models or mismatching known metrics are not accepted as valid readings and cannot renew leases.

```json
{"schema":1,"device_id":"001122334455","model":"tc1","boot":123,"sequence":1,"sensors":{"power":{"valid":true,"value":12.3,"unit":"W","age_ms":100}}}
{"schema":1,"device_id":"aabbccddeeff","model":"a1","boot":456,"sequence":2,"sensors":{"fan_speed_percent":{"valid":true,"value":60,"unit":"%","age_ms":0}}}
```

Every declared known field requires strict boolean `valid`, `value`, exact `unit`, and nonnegative integer `age_ms`. valid=true requires a finite number, exact unit, source age below 20000 ms and the bounds below. valid=false requires value=null, never fake zero. Include at least one known metric. Unknown additive fields may be ignored without skipping validation of known fields.

| Sensors field | Unit | Range and meaning |
| --- | --- | --- |
| `temperature`, `humidity` | `°C`, `%` | -40..125, 0..100 |
| `pm25`, `pm10` | `µg/m³` | Finite, nonnegative |
| `formaldehyde` | `mg/m³` | Finite, nonnegative |
| `co2` | `ppm` | 1..65535 |
| `pressure` | `Pa` | Finite, nonnegative; convert other units numerically before labeling Pa |
| `power`, `energy` | `W`, `kWh` | Finite, nonnegative; the current new TC1 producer publishes power only |
| `tvoc` | `ppb` | Finite, nonnegative, according to real module capability |
| `fan_speed_percent` | `%` | 0..100; A1 effective main-fan output `effective_on ? effective_speed : 0`, matching status.percentage; not measured RPM or fresh-air-fan RPM |

M1 local sources resolve its own climate, PM2.5, HCHO and optional SCD40 CO₂, with local BMP3 pressure numerically converted to Pa. This M1 firmware change does not publish those readings on the generic `sensor/<device_id>/state` topic; accepting valid M1 typed messages does not establish an existing producer. DAIKIN may also provide PM10/TVOC according to installed modules. Consumers use actual fields and validity. TC1 reports power=null/valid=false before a real computed power sample, on invalid sampling or when source age reaches20s. No new pulses must not continually relabel old power as age0, and initial zero is not measurement readiness. A1 reports an effective-output snapshot and uses null/false before readiness.

Boot and sequence are strict JSON integers1..4294967295, not strings or floating-point tokens. Sequence increments with uint32 wrap, skipping zero. Within one boot, use wrap-aware ordering; duplicates/older values do not renew leases. New boots retire previous boots; a bounded RAM cache rejects recent retired-boot replay. Never emit negative counters through a signed32-bit JSON constructor.

Compute leases from source age plus monotonic elapsed time after receipt, bounded by both20s and the lane's configured TTL. Duplicates, retained replay, availability=online alone and reconnects cannot refresh an old value. Reconnect clears caches until fresh data arrives. A new invalid field invalidates its metric. Resolve both lanes from one accepted frame without dropping the second through global deduplication. Never republish user display values as physical measurements.

The [Schema](contracts/schemas/sensor-values-v1.schema.json) checks structure/ranges. Account authorization, topic identity, replay, source health, configured TTL and live publication remain runtime checks. This development extension does not establish implementation or hardware acceptance across older devices.

## Legacy

TC1 retains Legacy `device/ztc1/<MAC>/...` and existing HA identities. Legacy and TMCP are separate; upgrading firmware does not silently convert the protocol. M1/A1 do not impersonate Legacy TC1. The cloud platform continues to accept v0.9.x devices.
