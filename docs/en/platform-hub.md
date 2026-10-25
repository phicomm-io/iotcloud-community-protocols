# Platform API and hub draft

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/platform-hub/)

## Existing platform API

The frontend uses configurable `apiOrigin` and `mqttWS`. HTTPS pages cannot connect to insecure HTTP/WS services. A LAN hub can host the frontend at its own HTTP origin. Platform sessions and device Web Basic passwords are separate authentication domains.

| Path | Method and purpose |
| --- | --- |
| `/api/auth/login` | POST `{username,password}`, returns account information |
| `/api/auth/me` | GET current account |
| `/api/auth/logout` | POST revoke session |
| `/api/auth/password` | POST `{current_password,password}` to change the website password |
| `/api/auth/mqtt-password` | POST change MQTT password with implementation-specific password confirmation |
| `/api/devices` | GET device list; POST register a device |
| `/api/devices/...` | PUT / DELETE with account namespace checks |
| `/api/integrations/bemfa` | GET / PUT Bemfa integration settings |

The frontend uses `credentials:include` and supports `Authorization: Bearer <token>`. Login exposes the token through `X-IotCloud-Session`. Account fields include `username`, `mqtt_username`, `aliases`, `is_admin`; optional fields have frontend defaults. Cross-origin deployments explicitly allow origins; cookie-authenticated writes validate Origin. Stable error `code` drives behavior, while `Accept-Language` may select display text.

This describes shared integration points. The platform owns its full cloud account lifecycle. Hub implementations should reuse frontend-compatible fields and responses, declaring unsupported cloud features explicitly.

## DAIKIN hub: draft, awaiting implementation

Use a separate `variant:"hub"`, shown as “Hub edition” / “中枢版本”. Ordinary `full` remains a sensor device. The following scope is agreed; ports, capacity, forwarding configuration and new APIs still need schemas and tests before implementation. This draft does not claim existing functionality.

- Independent local accounts; MQTT TCP/WebSocket Broker accessible to LAN devices and HA; login and management through the existing frontend.
- Local and cloud accounts remain independent. Email registration, mail delivery and GitHub sign-in are outside the initial scope.
- Broker and upstream MQTT client run together with independent connections, authorization, queues and reconnect state.
- Explicit mappings relay Bemfa and upstream events while preserving the hub's own sensor reporting.

## Cross-repository requirements

The local Broker uses [TMCP account namespaces](mqtt.md). Connection authentication determines ownership. Retained messages, LWT, wildcard subscriptions and HA discovery deliveries obey account ACLs. Device registration/deletion and account disablement update authorization.

Forwarding needs an explicit direction, source and destination. Avoid unconditional bidirectional copying. Rules must define event identity, deduplication, source/hop limits and retained behavior after reconnect. Commands/results must not loop. Bound connections, packet size, subscriptions, retained storage, queues and timeouts; explicitly reject exhausted capacity.

Firmware, frontend and release tools all recognize `hub`: build matrix, download names, OTA catalog and backup/restore validate the variant. Validate same-origin account login, TCP/WS, HA, Bemfa and concurrent upstream scenarios before changing draft status to implemented.
