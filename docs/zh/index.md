# IoTCloud 开发文档

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/) · [项目主页](https://phicomm-io.github.io/)

本仓库集中定义固件、M1 传感器 MCU、WebUI 和管理平台之间的接口。开发者从这里核对数据格式、能力协商、失败行为和兼容性，再到实现仓库修改代码。

| 开发内容 | 从这里开始 |
| --- | --- |
| 新增跨仓库功能、修改配置格式 | [接口演进与协作](conventions.md) |
| 局域网控制、WebUI、配置命令 | [设备 HTTP](device-http.md) |
| MQTT、HA、外部传感器 | [MQTT 与传感器](mqtt.md) |
| 备份、语言、OTA 分流 | [配置与升级](configuration.md) |
| Wi-Fi MCU 与 M1 传感器 MCU 联调 | [UART](m1-uart.md)、[显示源与按钮](m1-display.md) |
| 平台接入、大金中枢版本 | [平台与中枢](platform-hub.md) |

## 规范状态

当前是面向 v1.0.0 的开发规范。`implemented-unreleased` 表示已有开发实现，尚未标记正式发布；`draft` 表示待实现草案。各接口状态和实现入口见 [接口索引](contracts/registry.json)。实际设备必须先查询能力，不能仅根据版本号显示功能入口。

## 实现仓库

| 仓库 | 职责 |
| --- | --- |
| [iotcloud-community-firmware](https://github.com/phicomm-io/iotcloud-community-firmware) | Wi-Fi 固件、设备接口、配置迁移、OTA、中枢 |
| [phicomm_m1_mcu_atsamd20](https://github.com/phicomm-io/phicomm_m1_mcu_atsamd20) | M1 传感器 MCU、显示、按键与主控升级 |
| [iotcloud-community-frontend](https://github.com/phicomm-io/iotcloud-community-frontend) | 设备 WebUI、管理平台前端与演示 |
| [iotcloud-community-mqtt](https://github.com/phicomm-io/iotcloud-community-mqtt) | 云账户、设备登记、Broker 权限与平台 API |
| [phicomm-io.github.io](https://github.com/phicomm-io/phicomm-io.github.io) | 使用指南、下载与用户入口 |

接口定义以本仓库的固定提交为准，设备使用说明在项目主页维护。文档中的设备 ID、用户名和数值均为示例。
