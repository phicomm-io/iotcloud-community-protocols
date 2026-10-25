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

<a id="sensor-values-v1"></a>

## 通用 typed feed：sensor-values-v1

新增 profile `sensor-values-v1` 沿用上述账户作用域主题和 wire schema1，并定义可选的多物理量字段，不改变 `sensor-co2-v1` 的既有含义或把功率塞进 CO₂ 字段。消息必须非 retained；普通 retained device state 不能替代该 feed。`device_id` 必须匹配主题，不能改用 `id`。可选 `model` 只能为m1/daikin/tc1/a1，是元数据，不授予跨账户权限。声明model时已知metric必须属于该producer子集：M1为温湿度/PM2.5/甲醛/CO₂/压力，DAIKIN另可PM10/TVOC，TC1为power/energy，A1为fan_speed_percent。未知model或不匹配的已知metric不接纳为有效数据，也不续租。

```json
{"schema":1,"device_id":"001122334455","model":"tc1","boot":123,"sequence":1,"sensors":{"power":{"valid":true,"value":12.3,"unit":"W","age_ms":100}}}
{"schema":1,"device_id":"aabbccddeeff","model":"a1","boot":456,"sequence":2,"sensors":{"fan_speed_percent":{"valid":true,"value":60,"unit":"%","age_ms":0}}}
```

每个已声明字段必须有 `valid`（严格布尔值）、`value`、`unit`、`age_ms`（严格非负整数）。valid=true 要求数值有限、单位严格匹配、源年龄小于20000ms并符合下表；valid=false 必须 value=null，不以0代替失效。消息至少含一种已知 metric；可忽略未知附加字段，但不得据此跳过已知字段的校验。

| sensors 字段 | unit | 有效范围与语义 |
| --- | --- | --- |
| `temperature` / `humidity` | `°C` / `%` | -40..125 / 0..100 |
| `pm25` / `pm10` | `µg/m³` | 有限非负 |
| `formaldehyde` | `mg/m³` | 有限非负 |
| `co2` | `ppm` | 1..65535 |
| `pressure` | `Pa` | 有限非负，其他单位先换算数值；不能只改 unit 标签 |
| `power` / `energy` | `W` / `kWh` | 有限非负；当前新增 TC1 producer只提供 power |
| `tvoc` | `ppb` | 有限非负，以实际模块能力为准 |
| `fan_speed_percent` | `%` | 0..100；A1 当前生效主风机输出 `effective_on ? effective_speed : 0`，对应 status.percentage；不是实测 RPM，fresh-air 变体也不代表新风 RPM |

M1 现有物理 feed 提供温湿度、PM2.5、甲醛与可选 SCD40 CO₂；本地 BMP3 压力可由 M1 resolver 换算为 Pa，但不因此声称旧远端 feed 已有压力。DAIKIN 按模块能力还可提供 PM10/TVOC；消费者须以真实字段和 valid 为准。TC1 未取得实际功率计算样本、样本异常或源年龄满20s时发布 power=null/valid=false；没有新脉冲不能不断把旧功率重标 age0，也不能用启动默认0宣称采样就绪。A1 使用当前生效输出快照，未就绪时同样为 null/false。

boot、sequence 为1..4294967295的严格 JSON 整数，不接受字符串或浮点token；发布计数器递增，uint32回绕跳过0。消费者在同boot下用带回绕的顺序比较，重复/倒序不续租；新boot退休旧boot，有限 RAM 缓存拒绝最近退出boot的重放。uint32不能通过有符号32位 JSON 构造错误地输出负数。

租期从真实源年龄加接收后单调时间计算，必须同时小于20s与该路配置TTL。重复数据、retained重放、仅 availability=online 或 MQTT 重连不能把旧数值变新；重连清缓存等待新数据。已知无效新帧使对应 metric 失效，两个 lane 来自同一新帧时分别解析，不能因全局去重丢掉第二路。显示值仍不得反向发布成真实测量，避免回路。

该 profile 的结构与范围由 [Schema](contracts/schemas/sensor-values-v1.schema.json) 约束；账户、主题一致、replay、源健康、配置TTL与发布时效是运行时检查。此接口属于开发扩展，不能据此宣称全部旧固件或设备硬件已经实现。

## 旧协议

TC1 保留 Legacy `device/ztc1/<MAC>/...` 与既有 HA 标识。Legacy 和 TMCP 分开接入，不因版本升级自动互转。M1 / A1 不以 Legacy 格式冒充 TC1；云平台继续兼容 v0.9.x 设备。
