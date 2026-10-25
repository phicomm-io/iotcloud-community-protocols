# MQTT and sensors

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/mqtt/)

TMCP (Tom MQTT Cloud Protocol) uses `protocol:"tmcp"`, `protocol_version:2`, `version:"v2"`. Normalize a MAC to 12 lowercase hex digits. Account scope is `u_` followed by the hex encoding of the MQTT username's UTF-8 bytes; a Broker with no username uses `local`.

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

## Legacy

TC1 retains Legacy `device/ztc1/<MAC>/...` and existing HA identities. Legacy and TMCP are separate; upgrading firmware does not silently convert the protocol. M1/A1 do not impersonate Legacy TC1. The cloud platform continues to accept v0.9.x devices.
