# Platform API and DAIKIN hub

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/platform-hub/)

Hub contracts are **implemented-unreleased**: they describe development source, without a new v1 firmware release or acceptance of Apple Home pairing, physical outputs or long-running operation. Registry paths beginning `firmware/` identify the [firmware repository](https://github.com/phicomm-io/phicomm-community-firmware). Consumers pin this specification through `protocols.lock.json` and record the implementation commit separately at delivery.

## Shared platform integration

The frontend uses `apiOrigin` and `mqttWS`. Shared endpoints include `/api/auth/login`, `me`, `logout`, `password`, `mqtt-password`, `/api/devices` and `/api/integrations/bemfa`. Cloud platforms may provide cookies, Bearer and cross-origin access. The hub described below provides same-origin HTTP and Bearer sessions; cloud cookies and administrator permissions do not apply.

Platform HTTP selects `en` / `zh-CN` through `Accept-Language`, defaulting to `zh-CN` when absent or unrecognized. Responses include `Content-Language` and `Vary: Accept-Language`. Error `error` and success `message` fields are translated text; stable `code` / `message_key` values do not change with language. Success responses may add `message_key`. Clients branch on stable fields and preserve user-authored account/device names.

Administrator `GET /api/admin/verification-emails` may add `detail_key` to `records[]`, for example `verification.interrupted`, `verification.delivery_failed` or `e.66ba1c71fe55`. `detail` follows the request language, including compatibility with existing Chinese database records. Language selection changes neither mail status, verification-code fields nor user input. Implementation: `platform/backend/{main,util,i18n,verification_emails}.go`. These platform HTTP additions do not alter MQTT payloads or require administrator endpoints on the hub.

HTTPS pages cannot directly connect to the hub's HTTP/WS services. The hub serves its frontend from `/iotcloud/`. It provides no email registration, mail delivery, GitHub sign-in, aliases or administrator accounts. `/api/auth/github/status` and `/api/banner` return `enabled:false`.

## Local owner and HTTP sessions

The hub uses the independent `variant:"hub"`; ordinary `full` remains the sensor edition. Set the device Web password first, then use device Basic authentication as `admin`:

```http
POST /api/hub/setup
Content-Type: application/json

{"username":"local","password":"local-password"}
```

Usernames contain 3–32 ASCII letters, digits or underscores. Passwords contain 8–63 UTF-8 bytes and no NUL. There is one local owner; cloud identities are not imported. Setup returns HTTP 409 when an owner already exists and cannot run without a device Web password. Password verifiers use separately salted PBKDF2-HMAC-SHA256. A failed configuration save returns HTTP 503 `storage_error` and preserves the previous configuration.

`POST /api/auth/login {username,password}` returns an account object and a 64-character hex token in `X-IotCloud-Session`. Send `Authorization: Bearer <token>` afterwards. The hub neither issues nor reads session cookies. Up to four memory sessions last 12 hours from login and disappear on reboot. Account fields are `username`, `mqtt_username`, `aliases:[]`, `is_admin:false`, `hub:true` and `mqtt_password_separate`. Counted account/MQTT password failures share a five-failure, 30-second backoff window.

HTTP accepts the device IP, AP IP or `daikin-<device_id>.local` as Host. Writes carrying Origin must match `http://<Host>`; OPTIONS does not enable cross-origin access. Bodies are limited to 12288 bytes; POST/PUT use `application/json`. Owner sessions, device Basic authentication and upstream cloud credentials are separate authentication domains.

| Path | Methods, input and behavior |
| --- | --- |
| `/api/register/status` | Public GET; `hub:true`, `setup_required`, `mqtt_uri`, `mqtt_ws_uri`, cloud registration `enabled:false` |
| `/api/auth/me` | GET with local owner session |
| `/api/auth/logout` | POST `{}`, revoke the current session |
| `/api/auth/password` | POST `{current_password,password}`, revoke sessions; update MQTT password too unless separated |
| `/api/auth/mqtt-password` | POST `{current_password,password}`; current password means the account password; separate MQTT credentials and disconnect Broker clients while retaining HTTP sessions |
| `/api/devices` | GET; POST `{mac,model,version:"v2"}`; server assigns the owner and `status:"active"` |
| `/api/devices/<mac>` | DELETE registration and related Bemfa mappings; disable Bemfa when its last mapping disappears |
| `/api/hub/bridge` | GET/PUT explicit upstream routes |
| `/api/integrations/bemfa` | GET/PUT/DELETE Bemfa mappings |
| `/api/hub/homekit` | GET/PUT HAP settings and status |
| `/api/hub/homekit/pairing` | DELETE `{"confirm":true}`, clear pairing and schedule reboot |

Apart from the documented setup/public endpoints, these require a local session. Branch on stable `code`: 401 `unauthorized`, 400 `invalid_params`, 409 `conflict`, 429 `hub_rate_limited`, 503 `storage_error` or `busy`. Register up to 12 devices of model `a1`, `m1`, `tc1` or `daikin`. MACs are lowercase 12-digit hex IDs, excluding all-zero/all-f values.

## Local MQTT Broker

| Item | Development implementation |
| --- | --- |
| TCP | `mqtt://<host>:1883` |
| WebSocket | `ws://<host>:9001/mqtt`, WebSocket 13, subprotocol `mqtt` |
| MQTT | 3.1.1; Clean Session, nonempty client ID, username and password required; QoS 0/1 publication and QoS 0 subscription grants; no TLS or persistent sessions |
| Authentication | Owner's MQTT password; initially the account password, independently changeable |
| Limits | 8 connections, 24 subscriptions/client, 256-byte topics, 8192-byte packet/message boundary, at most 128 retained entries totaling 49152 bytes |
| Shared budgets | Receive 24576, wills 4096, subscription strings 8192 bytes; refuse/close on exhaustion, without offline-delivery guarantees |

TMCP publication/delivery is restricted to `phicomm/v2/u_<username-UTF8-hex>/...`. Wildcard delivery still checks the actual topic. Authenticated owners may use non-`phicomm/v2/` topics for HA and custom routes. This is one owner's trusted LAN Broker, without per-device credentials or registered-MAC ACLs. Registration/deletion affects management, Bemfa and HomeKit; it does not revoke other MQTT clients' access to the same owner's namespace.

LWT, wildcard subscriptions and retained messages obey these permissions. Retained publications/wills are forbidden on `/command` or `/set` suffixes. Retained replay delivers to subscribers without creating a new forwarding event. Account/MQTT credential changes clear connections, wills and retained state. Broker, upstream MQTT client and Bemfa client run concurrently; upstream credentials never authorize local login.

## Explicit upstream forwarding

```json
{"enabled":true,"mqtt":{"host":"broker.lan","port":1883,"user":"upstream","password":"upstream-password"},"mappings":[{"direction":"out","local_topic":"home/local","remote_topic":"home/remote","retain":true,"allow_retained":false}]}
```

PUT requires `enabled` and `mappings`, at most eight routes. Optional `mqtt` requires `host`, `port`, `user`; omitted `password` preserves the saved value. GET exposes only `password_set`. Use concrete topics without `+`, `#` or NUL. Unique source keys are remote topic for `in`, local topic for `out`. TMCP local topics must belong to the owner.

- `out` forwards local/internal publications upstream. Its retained flag is the intersection of publication retained and route `retain`.
- `in` injects upstream events locally. Reject upstream retained unless `allow_retained:true`; the local retained flag follows route `retain`.
- If either endpoint ends in `/command` or `/set`, both retained flags must be false.
- Injected upstream/Bemfa events are not forwarded out again. A shared cache holds up to 16 topic+payload digests, separated by source, suppressing self-echoes for five seconds. This is neither permanent deduplication nor an exactly-once execution guarantee.

Reconnect and retained replay do not create outbound events. Ownership, duplicate route keys, freshness and loop boundaries require runtime checks beyond JSON Schema.

## Bemfa

PUT accepts `enabled`, `mappings` and `api_key` when enabled. Empty `api_key` preserves an existing key. GET hides the key and returns `key_set`, `max_mappings:8`, `status`; DELETE removes the integration. Each mapping contains the registered device's complete `{mac,model,version,status,username}` object. Up to eight mappings have unique topics and device/channel pairs.

| Device/channel | Topic suffix | Commands | Reported state |
| --- | --- | --- | --- |
| TC1 0–5 | `001` | `on`/`off` → `outlet.set` | Corresponding `socket_states` entry |
| A1 fan 0 | `003` | `on`, `off`, `on#1`–`on#4` → 20/50/75/100% | Nearest level from applied output |
| A1 light 1 | `002` | `on`, `off`, `on#1`–`on#100` → percent `light.set` | Convert raw 0–255 brightness to percent |

Fresh-air A1 is identified by `fresh_air_on`/`fresh_air_speed` and uses `fresh_air.set`; ordinary A1 uses `fan.set`. Requested settings never replace applied output. Retained commands are rejected; commands require local/internal online device state younger than 20 seconds. Injected upstream availability, state and result messages, retained or otherwise, cannot refresh local device evidence or complete a pending command. Each TMCP command has an independent random request ID. No matching local receipt within 10 seconds yields `device_timeout`. Bemfa `connected`/`accepted` establishes a forwarding receipt, not physical load/fan output. A state event reports a changed value, or an unchanged value last forwarded over 30 seconds ago.

## HomeKit HAP

The optional HAP Bridge uses port 51826 and `protocol:"hap"`. **Matter commissioning and device services are not provided.**

```json
{"enabled":true}
```

This is the complete `PUT /api/hub/homekit` input. Success returns HTTP 202 `{"code":"accepted","restart_required":true}`. Failed persistence preserves settings and current sessions. GET returns `enabled`, `protocol`, `ready`, `code`, `paired`, `devices`, `port`. Only a healthy, initialized, unpaired bridge exposes `setup_code` and `setup_uri` to its authenticated owner; failures and paired bridges omit them. Codes include `disabled`, `ok`, `storage_error`, `identity_changed`, `invalid_params`, `restart_required`.

`DELETE /api/hub/homekit/pairing {"confirm":true}` stops HAP before attempting erase. Failure returns 503 and leaves HAP disabled; success returns 202 and reboots. Ordinary configuration backups exclude pairing storage. Changing owner identity/device registration stops the previous HAP service and requires reboot, preventing old sessions from controlling a removed device.

| Source | HAP services |
| --- | --- |
| TC1 | Six Switch services, still named Outlet 1–6; no per-outlet insertion sensor, so no OutletInUse |
| A1 | Fan and LightBulb; fresh-air variants control the independent fresh-air fan |
| M1/DAIKIN | Temperature, humidity, CO₂ and PM2.5; DAIKIN additionally PM10, based on valid measurements |

Trust local/internal publications only. Upstream injection and retained replay cannot confirm a HomeKit operation. Device state must be reachable within 30 seconds; sensor total age must be below 20 seconds. Report unavailable data as unavailable, without substituting zero. Batched fan/light power and level changes cause one mutation, with explicit off taking priority. `light.set` brightness is 0–100%; reported device brightness is 0–255. Controls require a matching successful TMCP receipt followed by a fresh applied snapshot or active `status.get` result, within 2.5 seconds. Requested values never optimistically become reported state.

Pairing storage uses a private marker/NVS only in the unpartitioned tail `0x3d0000`–`0x3fffff` of the known 4 MiB dual-OTA layout. It does not modify the installed partition table, erase default NVS or initialize unknown nonempty data. NVS read/write/commit failure during initialization or runtime closes HAP listeners/sessions and disables pairing/control. Factory reset can erase recognized corrupt pairing storage. Unidentified tail bytes remain untouched; ordinary settings reset does not claim to clear them.

This is the wired-install layout in `firmware/DAIKIN/partitions.csv`, with `0x1e0000` (1966080-byte) application slots. Factory devices may still have 1.5 MiB slots. The current approximately 1.91 MB Hub HAP development image exceeds that factory slot; the wired layout does not establish compatibility with ordinary OTA. A successful build or upload does not establish installed partition compatibility. Read the device's actual partition layout before deployment.

Local Hub API/MQTT accepts only the local owner. The device's explicitly configured native upstream TMCP can still manage the hub device itself, including `config.set` / `system.reset`. This separate management trust entry does not grant a local owner Bearer session. HAP pairing credentials appear only in a healthy unpaired owner GET response, never in ordinary state, config or configuration backups.

Implementation entry points: `firmware/DAIKIN/include/hub_{service,broker,transport,relay,home}.h`, `firmware/DAIKIN/src/{hub,home,http}.inc`, and the private HomeSpan adapter. Validation: `firmware/DAIKIN/tests/hub/`, `firmware/DAIKIN/tests/test_hub_mqtt.py`. See [schemas and examples](contracts.md). Record host tests, firmware builds, Apple Home pairing and physical-device acceptance separately.
