# 备份、语言与升级

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/configuration/)

## 完整备份

v1 设备声明 `config_backup:1` 后，前端通过有密码的局域网 HTTP 下载或恢复完整配置。备份包含 Wi-Fi、MQTT 等敏感字段。v0.9.x 的公开配置导出是部分备份，不能按完整备份恢复。M1 传感器 MCU 音乐不在 Wi-Fi 配置内。

MiCO（TC1 / A1 / M1）schema 1 采用 104 字节头和机型原生配置负载，总长最多 16384 字节：

| 偏移 | 字节数 | 内容 |
| --- | --- | --- |
| 0 | 8 | ASCII `PHCBACK1` |
| 8 | 8 | NUL 结尾机型 |
| 16 | 40 | NUL 结尾 variant |
| 56 | 32 | NUL 结尾固件版本 |
| 88 | 4 | schema，当前 1 |
| 92 | 4 | 配置存储版本 |
| 96 | 4 | 负载字节数 |
| 100 | 4 | 负载 CRC-32，反射多项式 `0xedb88320`，初值/末异或均为 `0xffffffff` |

32 位整数为小端。负载是具体机型和存储版本的快照；必须匹配机型、variant、配置版本、精确长度和 CRC，并继续验证字段语义。它不是跨架构通用序列化格式。

DAIKIN 使用独立 JSON 信封：`schema`、`model`、`variant`、`firmware`、`config_version`、`config`。不能把 MiCO 文件、普通 `full` 和未来 `hub` 备份混用。恢复先校验全部内容，再一次持久化；失败保留原设置。

<a id="m1-display-storage-v9"></a>

## M1 双路配置存储v9

双路显示配置追加在原v8负载尾部，旧配置前缀与 CO₂ 字段偏移不变。v8启动迁移保留普通配置、旧 CO₂、阈值、蜂鸣器、automation与revision；默认仍选legacy profile，新双路两位置为none、无RAM租期。只有显式新SET才启用dual，迁移不自动接管显示。

v8完整备份是明确的兼容例外：先校验原model/variant、v8精确长度、CRC及旧字段，再有界迁移到v9并初始化新尾段。v9备份继续要求v9精确长度与语义；未知未来版本拒绝。候选配置与profile同笔持久化，失败完整回滚；短期API数值和剩余租期不进入备份。

## 恢复模式

`config.get` 中的 `migration_state` 为 `ready` 或 `confirmation_required`；后者表示当前使用 RAM 中的恢复配网设置，原始配置仍待用户处理。前端展示明确的清空确认，执行设备支持的重置动作。恢复期间不能通过普通设置或自动任务覆盖原 Flash。

## 语言

设备 `config.get.language` 使用 `zh-CN` / `en`，默认 `zh-CN`。通过设备 `config.set` 的 `values.language` 修改，和名称设置一样持久化。

```json
{"request_id":"language_1","action":"config.set","params":{"values":{"language":"en"}}}
```

浏览器语言单独保存，可自动或手动选择。设备语言决定 MQTT Discovery 的传感器名称；切换后重新公告，实体 ID、主题、唯一标识和用户名保持稳定。配置备份保留设备语言。

## OTA 分流与依赖

v1 开发约定使用 `/ota/v1/<model>/<variant>/latest.json`。旧路径在正式桥接版本验收后固定到 v1.0.0，不持续向 v0.9.x 设备推送未来不兼容版本；分流上线是独立发布步骤。

OTA 选择必须同时核对机型、variant、签名和版本。DAIKIN `hub` 是独立中枢版本，不能由普通 `full` 自动跨变体升级。浏览器直接读取并校验发布差异；不可用时说明原因并要求额外确认。

声明 `ota_variant_conversion:"full-to-hub"` 的 DAIKIN `full` 开发固件可使用独立的[显式签名转换接口](device-http.md#daikin-full-hub)。普通签名/未签名 OTA 仍保持同 variant；转换不改分区表，且不支持 `hub` → `full`。

Wi-Fi 固件、传感器 MCU 和前端制品分别记录版本。固件使用完整提交与 SHA-256 固定的前端发布制品；构建或 UART 接收成功不代表新固件已经运行。
