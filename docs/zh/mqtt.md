# MQTT 与传感器

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/mqtt/)

TMCP（Tom MQTT Cloud Protocol）使用 `protocol:"tmcp"`、`protocol_version:2`、`version:"v2"`。设备 MAC 去掉分隔符，转为小写 12 位十六进制。账户 `scope` 是 `u_` 加 MQTT 用户名 UTF-8 字节的十六进制；无用户名的自建 Broker 使用 `local`。

## 设备主题

设备根为 `phicomm/v2/<scope>/<model>/<mac>`。`model` 使用 `tc1`、`m1`、`a1` 或 `daikin`，以设备公告为准。

| 主题或后缀 | Retain | 载荷 |
| --- | --- | --- |
| `phicomm/v2/<scope>/discovery/<mac>` | 是 | schema 1、model、完整 TMCP 协议标记 |
| `<root>/availability` | 是 / LWT | `online` / `offline` |
| `<root>/state` | 是 | 设备状态快照 |
| `<root>/capabilities` | 是 | 动作列表及能力 |
| `<root>/command` | 否 | [命令信封](device-http.md) |
| `<root>/result` | 否 | 对应 `request_id` 的结果 |

Broker 权限以主题中的账户归属为准，不信任载荷中的用户字段。只能访问本账户明确授权的设备；不同账户可拥有相同 MAC，不能仅以 MAC 做全局设备键。retained 命令必须拒绝。

HA 发现主题为 `homeassistant/<component>/<scope>/<model>_<mac>_<entity>/config`。HA 通用发现订阅可以开放，但每条投递仍需检查账户归属；不得因此授予跨账户读取或通配发布。设备语言只改变实体名称，不能改变实体唯一标识、主题和账户键。

## 跨设备传感器 schema 1

主题：`phicomm/v2/<scope>/sensor/<device_id>/state`。发布者只报告真实采集数据；消费者不把转发到显示器的值再作为本机传感器发布。

```json
{"schema":1,"device_id":"123456abcdef","boot":123,"sequence":1,"sensors":{"co2":{"valid":true,"value":1234,"unit":"ppm","age_ms":0}}}
```

| 字段 | 规则 |
| --- | --- |
| `schema` | 整数 1 |
| `device_id` | 必须与主题内小写 ID 一致 |
| `boot`、`sequence` | 整数 1..4294967295；boot 区分本次启动，sequence 在本次启动递增 |
| `sensors.co2.valid` | JSON 布尔值 |
| `value` / `unit` | 有效 CO₂ 为有限数 1..65535，单位严格为 `ppm` |
| `age_ms` | 非负整数，发送时的样本年龄；接收后继续累加本地经过时间 |

通用传感器字段还可包括 `temperature`（`°C`）、`humidity`（`%`）、`pm25`（`µg/m³`）、`formaldehyde`（`mg/m³`）。本文提供的 Schema 专门校验 CO₂ 接入及样例，其他字段不能据此跳过各自单位和范围检查。

M1 只接受已配置来源、本账户的实时消息。忽略 retained 重放、错误 ID、重复/倒序序号与最近已退出的启动标记；启动标记缓存保存在 RAM，不能代替 Broker 认证与权限。新序号但无效 CO₂ 的消息会使旧 CO₂ 立即失效。`age_ms + 接收后经过时间 >= 20000` 时失效，不再延长显示租期。MQTT 会话重建会清除远端缓存，等待新鲜发布。

既有固件还可能提供平铺传感器字段，v1 新实现优先使用上述 `sensors` 结构。不能用 retained 的在线快照证明读数新鲜。

## 旧协议

TC1 保留 Legacy `device/ztc1/<MAC>/...` 与既有 HA 标识。Legacy 和 TMCP 分开接入，不因版本升级自动互转。M1 / A1 不以 Legacy 格式冒充 TC1；云平台继续兼容 v0.9.x 设备。
