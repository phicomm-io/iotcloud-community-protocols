# IoTCloud 开发文档

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/) · [项目主页](https://phicomm-io.github.io/)

本仓库集中定义固件、M1 传感器 MCU、WebUI 和管理平台之间的接口。开发者从这里核对数据格式、能力协商、失败行为和兼容性，再到实现仓库修改代码。

| 我要做的事 | 从这里开始 |
| --- | --- |
| 新增跨仓库功能、改接口或配置格式 | [接口演进与跨仓库协作](conventions.md) |
| 调设备 HTTP、命令、WebUI | [HTTP 与命令](device-http.md) |
| 接 MQTT、Home Assistant、外部传感器 | [MQTT 与传感器](mqtt.md) |
| 看采样新鲜度与 PM 夜间节能 | [采样年龄与 PM 节能](sensor-age.md) |
| 改备份格式、语言、OTA 分流 | [配置、备份与升级](configuration.md) |
| 联调 M1 两颗 MCU 的串口帧 | [UART 与能力查询](m1-uart.md) |
| 改 M1 显示内容、灯位或按键 | [显示源与按钮事件](m1-display.md) |
| 接大金 G3 屏幕、推送图片或视频流 | [G3 推送、摄像头与屏幕](daikin-g3-media.md) |
| 接管理平台、做中枢版本 | [平台接口与中枢](platform-hub.md) |
| 找 Schema、样例、测试向量 | [Schema 与样例](contracts.md) |

## 怎么用这些文档

正文说明字段含义、边界和失败行为；机器可读定义在 `contracts/`，两者一起审查。改动顺序是：先在本仓库确定接口，再在实现仓库改代码，实现 PR 引用同一个规范提交。

当前是面向 v1.0.0 的开发规范。每个接口的状态、生产者、消费者和实现入口见 [接口索引](contracts/registry.json)：`implemented-unreleased` 表示已有开发实现但未标记正式发布，`deprecated` 表示仅为兼容保留。实际设备必须先查询能力，不能仅根据版本号显示功能入口。

## 实现仓库

| 仓库 | 职责 |
| --- | --- |
| [iotcloud-community-firmware](https://github.com/phicomm-io/iotcloud-community-firmware) | Wi-Fi 固件、设备接口、配置迁移、OTA、中枢 |
| [phicomm_m1_mcu_atsamd20](https://github.com/phicomm-io/phicomm_m1_mcu_atsamd20) | M1 传感器 MCU、显示、按键与主控升级 |
| [iotcloud-community-frontend](https://github.com/phicomm-io/iotcloud-community-frontend) | 设备 WebUI、管理平台前端与演示 |
| [iotcloud-community-mqtt](https://github.com/phicomm-io/iotcloud-community-mqtt) | 云账户、设备登记、Broker 权限与平台 API |
| [phicomm-io.github.io](https://github.com/phicomm-io/phicomm-io.github.io) | 使用指南、下载与用户入口 |

接口定义以本仓库的固定提交为准，设备使用说明在项目主页维护。文档中的设备 ID、用户名和数值均为示例。
