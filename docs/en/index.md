# IoTCloud Developer Docs

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/) · [Project website](https://phicomm-io.github.io/)

Shared interfaces across Wi-Fi firmware, the M1 sensor MCU, device WebUI and management platform. Use these definitions to agree on formats, capabilities, failure handling and compatibility before changing implementations.

| Work | Start here |
| --- | --- |
| Cross-repository changes and storage formats | [Evolution and coordination](conventions.md) |
| LAN control, WebUI and commands | [Device HTTP](device-http.md) |
| MQTT, Home Assistant and external sensors | [MQTT and sensors](mqtt.md) |
| Backups, language and OTA routing | [Configuration](configuration.md) |
| M1 Wi-Fi / sensor MCU integration | [UART](m1-uart.md), [display sources and buttons](m1-display.md) |
| Platform clients and DAIKIN hub | [Platform and hub](platform-hub.md) |

## Specification status

This is the development specification for v1.0.0. `implemented-unreleased` identifies development implementations without a formal release; `draft` identifies work awaiting implementation. See the [interface registry](contracts/registry.json) for status and implementation paths. Query capabilities on the actual device before enabling a feature.

## Implementations

| Repository | Responsibility |
| --- | --- |
| [phicomm-community-firmware](https://github.com/phicomm-io/phicomm-community-firmware) | Wi-Fi firmware, device interfaces, migration, OTA and hub |
| [phicomm_m1_mcu_atsamd20](https://github.com/phicomm-io/phicomm_m1_mcu_atsamd20) | M1 sensor MCU, display, buttons and MCU updates |
| [phicomm-community-frontend](https://github.com/phicomm-io/phicomm-community-frontend) | Device WebUI, platform frontend and demos |
| [phicomm-community-mqtt](https://github.com/phicomm-io/phicomm-community-mqtt) | Cloud accounts, device registration, Broker ACLs and platform API |
| [phicomm-io.github.io](https://github.com/phicomm-io/phicomm-io.github.io) | User guides and downloads |

Implementations pin a specification commit. User instructions remain on the project website. Device IDs, accounts and readings in examples are synthetic.
