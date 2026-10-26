# MQTT 与传感器

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/mqtt/)

TMCP（Tom MQTT Cloud Protocol）使用 `protocol:"tmcp"`、`protocol_version:2`、`version:"v2"`。设备 MAC 去掉分隔符，转为小写 12 位十六进制。账户 `scope` 是 `u_` 加 MQTT 用户名 UTF-8 字节的十六进制；无用户名的自建 Broker 使用 `local`。

<a id="sensor-values-v2"></a>

## 通用设备字段：sensor-values-v2

本轮 RC.1 实现使用 **schema2**。旧 v1.0.0-rc 的 `sensor-values-v1` / schema1 标为 **deprecated（弃用）**，RC.1 不保证兼容旧 RC 数据源。该接口已实现，但调整后的 RC.1 尚未公开发布。主题仍为同账号非 retained 的 `phicomm/v2/<scope>/sensor/<device_id>/state`，不根据设备机型选择可用字段。

```json
{"schema":2,"device_id":"001122334455","model":"custom_meter","boot":123,"sequence":7,"sensors":{"load":{"name":"负载","type":"number","unit":"widgets/s","value":12.5,"valid":true,"age_ms":0},"future":{"name":"未来状态","type":"string","unit":"","value":"ready","valid":true,"age_ms":0}}}
```

| 字段 | 约定 |
| --- | --- |
| `schema` | 整数2；不重新解释旧 schema1 |
| `device_id` | 规范小写12位十六进制，必须等于主题中的设备身份 |
| `boot`、`sequence` | 整数1..4294967295；启动身份与单调递增序号用于实时防重放，不是墙钟时间 |
| `model` | 可选介绍信息，1..32 UTF-8字节；不作机型白名单或数据源绑定 |
| `sensors` | 含1..16字段的对象；键是稳定 `field_id`，ASCII `[a-z][a-z0-9_]{0,31}` |
| `name` | 必填显示名称，1..64 UTF-8字节；改名不改变字段身份 |
| `type` | 必填1..16位ASCII `[a-z][a-z0-9_]{0,15}`；当前仅消费 `number` |
| `unit` | 必填0..24 UTF-8字节，可为空；由发布者声明，不按机型或字段名推导 |
| `valid`、`value` | 布尔有效性；false必须为null，number为true时必须是有限JSON数字且转换float32后仍有限。布尔、数字字符串、非有限或溢出数值均不算数字；允许负数 |
| `age_ms` | 必填整数0..4294967295；有效字段必须小于20000ms，无效字段可报告更大帧龄 |

名称、单位必须是合法UTF-8，无孤立代理项、ASCII C0控制字符U+0000..U+001F或DEL U+007F；字节上限不等于字符数量。响应包和字段描述允许追加扩展，配置写入仍严格拒绝未知字段。每次实时值都携带描述，避免独立发现缓存过期或描述/数值版本错配。发布者为真实测量或生效输出选择稳定字段ID及准确名称/单位；TC1功率、A1生效风机百分比仅是例子，不是接收白名单。描述不能把请求设置伪装为测量值。

接收端先核对账号、主题身份、非retained实时来源、boot/sequence与时效，然后逐字段处理：未知type可为未来类型携带任意JSON值，但当前M1/前端必须**忽略其值**，不转换为数字或零。每个已接受的新boot/sequence都是**完整快照**：字段缺失、不支持、格式错误或无效时立即撤销旧number候选，不续有效数值租约；配置绑定保留，即使所有number消失也记录新boot/sequence，防旧数值帧重放恢复。一个不支持或无效字段不阻止同帧有效number兄弟字段使用。schema不合法的包不能作为有效样本证明。同一boot下重复/倒退序号、越权身份、retained、离线或过期来源均不能续期。

M1的MQTT来源绑定 `device_id + field_id + 预期type + 预期unit`，不绑定model/name；当前只可选number。已识别样本无效或预期单位不匹配时不能驱动该区域。已接受的新完整快照中，字段缺失、不支持或单位变化立即使旧number候选失效，相应区域回退而保留配置；name变化只更新名称。发布时帧龄加本地经过时间须同时满足20秒feed上限和区域TTL。负数可作为有效数据缓存，但M1非负玻璃格式返回 `out_of_range`。单位是元数据，不会给固定玻璃增加字形。见[profile4](device-http.md#m1-generic-profile4)。

[规范定义](contracts/sensor-values-v2.json) · [Schema](contracts/schemas/sensor-values-v2.schema.json) · [正反样例](contracts/examples/sensor-values-v2.json)。本仓库校验器执行 `x-utf8Bytes` 与 `x-float32Finite`；通用JSON Schema工具须另做等价运行时检查。


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

M1 的 local 来源可解析本机温湿度、PM2.5、甲醛与可选 SCD40 CO₂，并将本机 BMP3 压力换算为 Pa。本轮 M1 固件不在通用 `sensor/<device_id>/state` 主题发布这些读数；允许解析合法的 M1 typed 消息，不代表已有对应 producer。DAIKIN 按模块能力还可提供 PM10/TVOC；消费者须以真实字段和 valid 为准。TC1 未取得实际功率计算样本、样本异常或源年龄满20s时发布 power=null/valid=false；没有新脉冲不能不断把旧功率重标 age0，也不能用启动默认0宣称采样就绪。A1 使用当前生效输出快照，未就绪时同样为 null/false。

boot、sequence 为1..4294967295的严格 JSON 整数，不接受字符串或浮点token；发布计数器递增，uint32回绕跳过0。消费者在同boot下用带回绕的顺序比较，重复/倒序不续租；新boot退休旧boot，有限 RAM 缓存拒绝最近退出boot的重放。uint32不能通过有符号32位 JSON 构造错误地输出负数。

租期从真实源年龄加接收后单调时间计算，必须同时小于20s与该路配置TTL。重复数据、retained重放、仅 availability=online 或 MQTT 重连不能把旧数值变新；重连清缓存等待新数据。已知无效新帧使对应 metric 失效，两个 lane 来自同一新帧时分别解析，不能因全局去重丢掉第二路。显示值仍不得反向发布成真实测量，避免回路。

该 profile 的结构与范围由 [Schema](contracts/schemas/sensor-values-v1.schema.json) 约束；账户、主题一致、replay、源健康、配置TTL与发布时效是运行时检查。此接口属于开发扩展，不能据此宣称全部旧固件或设备硬件已经实现。

## 旧协议

TC1 保留 Legacy `device/ztc1/<MAC>/...` 与既有 HA 标识。Legacy 和 TMCP 分开接入，不因版本升级自动互转。M1 / A1 不以 Legacy 格式冒充 TC1；云平台继续兼容 v0.9.x 设备。
