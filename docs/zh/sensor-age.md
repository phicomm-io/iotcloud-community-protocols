# 传感器采样年龄与 PM 节能

本页定义增量 `sensor-values-v3`，对应当前 MessagePack schema 3 的 metadata/state 分离格式及 native LAN v3 的 PM 扩展。状态为 `implemented-unreleased`，实机精度与功耗需要针对具体板型验收。schema 2 的冻结定义保持原文。

[机器约定](contracts/sensor-values-v3.json) · [状态 Schema](contracts/schemas/sensor-values-v3.schema.json) · [描述符 Schema](contracts/schemas/sensor-metadata-v3.schema.json) · [正反样例](contracts/examples/sensor-values-v3.json)

metadata 主题为 `phicomm/v2/<scope>/sensor/<device_id>/metadata`，可 retained；state 主题同前缀加 `/state`，必须实时、非 retained。两者携带 `schema:3`、规范设备 ID、非零 `boot` 和 `descriptor_revision`；state 另有非零 `sequence`。metadata 的 `fields` 保存每项 name/type/unit，state 的 `sensors` 仅保存 value/valid/age_ms 及下述可选期限。消费者先匹配当前描述符，再按既有完整快照、启动标记和序号规则接收；未知类型、缺失、无效或单位不符的字段撤销旧数值，其他合法字段独立使用。

## 两种期限

仅 `pm25`、`pm10` 数字字段可携带 `max_age_ms`，严格整数 1..3600000，单位必须绑定 `µg/m³`。缺省采用既有短期限。DAIKIN G1/G2 普通动态模式发布 120000；启用且处于夜间节能时发布 3600000。`age_ms` 始终是实际采样年龄，不因发布、查询或重连归零。有效读数必须同时满足：

- 源年龄加接收后经过时间严格小于样本期限。
- 本次接收后的时间小于通信期限：A1 沿用十五秒，网页和 M1 不超过二十秒，配置的更短通信 TTL 继续生效。

Schema 校验数值类型和绝对上限；`age_ms < max_age_ms`、描述符单位绑定、重放和通信时效由运行时校验。MQTT availability、会话及 HA 发布超时继续独立工作。重复序号、旧 boot、retained state 不续租；时间到期、明确的模块故障或无效新样本使值失效，不用零代替。M1 发给 MCU 的显示租期取剩余样本期和通信期的较小值，UART 协议不变。

## UDP 与兼容性

[LAN 样本 body Schema](contracts/schemas/lan-pm-age-v1.schema.json) 在既有 native LAN v3 的 body 增加可选 `pm25_max_age_ms`。`ages[2]` 保留实际 PM2.5 年龄。仍然只有温度、湿度、PM2.5、甲醛、CO₂ 五项，不增加 PM10 槽。包身份、token、权限及重放规则不变。旧严格接收端可能拒绝扩展字段；启用长周期前需同步升级联动端。未携带扩展字段的消息继续原行为。

## 夜间 PM 设置

[配置 Schema](contracts/schemas/daikin-pm-power-v1.schema.json) 通过现有 `config.set` 的 `section:"pm_power"` 提交完整 `values`：enabled（布尔）、start_minute/end_minute（0..1439）、timezone_minutes（−720..840）。默认 false、1380、420、480。未知字段或范围错误返回现有 `invalid_params`，保存失败返回 `storage_error`，沿用现有鉴权与配置事务。`status.get`/`config.get` 的 `pm_power` 返回四项设置；整机 G3 不提供该能力。

按本地 `[start,end)` 判断，允许跨午夜；起止相同视为不生效，无可信时间保持动态测量。启动和非夜间 mode 5；夜间采用 59000 ms 策略间隔，每六十步开启 mode 5 一个间隔，其余 mode 1。每次开启后至少等待三十六秒，且取得完整校验、完成状态的应答后才能更新采样时间。退出夜间恢复 mode 5 和普通 120 秒样本期限。所有阶段继续报告真实年龄和通信状态。

原始 PM、CO₂、甲醛和温湿度输入以独立诊断保留，业务输出统一使用补偿结果。SGP30 基线是绑定传感器身份的私有缓存，不进入可转移配置；Wi-Fi 重置保留，完整出厂重置清除。
