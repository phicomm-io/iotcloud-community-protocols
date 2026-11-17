# IoTCloud Developer Docs

[简体中文](https://phicomm-io.github.io/iotcloud-community-protocols/) · [Project website](https://phicomm-io.github.io/)

Shared interfaces across Wi-Fi firmware, the M1 sensor MCU, device WebUI and management platform. Use these definitions to agree on formats, capabilities, failure handling and compatibility before changing implementations.

| What you want to do | Start here |
| --- | --- |
| Add a cross-repository feature, change an interface or config format | [Evolution and coordination](conventions.md) |
| Work on device HTTP, commands or the WebUI | [HTTP and commands](device-http.md) |
| Connect MQTT, Home Assistant or external sensors | [MQTT and sensors](mqtt.md) |
| Check sample freshness and night PM saving | [Sample age and PM power](sensor-age.md) |
| Change the backup format, language or OTA routing | [Configuration, backup and updates](configuration.md) |
| Integrate the two M1 MCUs over UART | [UART and capabilities](m1-uart.md) |
| Change M1 display content, lamps or buttons | [Display sources and buttons](m1-display.md) |
| Drive a DAIKIN G3 screen, images or streams | [G3 media, camera and screen](daikin-g3-media.md) |
| Build a platform client or a hub build | [Platform API and hub](platform-hub.md) |
| Find schemas, examples or test vectors | [Schemas and examples](contracts.md) |

## How to use these docs

The prose defines field meanings, bounds and failure behaviour; the machine-readable definitions live under `contracts/`. Review both together, and settle the interface in this repository before changing an implementation; implementation PRs reference the same specification commit.

This is the development specification for v1.0.0. Each interface's status, producers, consumers and implementation paths are in the [interface registry](contracts/registry.json): `implemented-unreleased` means a development implementation without a formal release, and `deprecated` is kept for compatibility only. Query capabilities on the actual device instead of inferring a feature from a version number.

## Implementations

| Repository | Responsibility |
| --- | --- |
| [iotcloud-community-firmware](https://github.com/phicomm-io/iotcloud-community-firmware) | Wi-Fi firmware, device interfaces, migration, OTA and hub |
| [phicomm_m1_mcu_atsamd20](https://github.com/phicomm-io/phicomm_m1_mcu_atsamd20) | M1 sensor MCU, display, buttons and MCU updates |
| [iotcloud-community-frontend](https://github.com/phicomm-io/iotcloud-community-frontend) | Device WebUI, platform frontend and demos |
| [iotcloud-community-mqtt](https://github.com/phicomm-io/iotcloud-community-mqtt) | Cloud accounts, device registration, Broker ACLs and platform API |
| [phicomm-io.github.io](https://github.com/phicomm-io/phicomm-io.github.io) | User guides and downloads |

Implementations pin a specification commit. User instructions remain on the project website. Device IDs, accounts and readings in examples are synthetic.
