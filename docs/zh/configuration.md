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

DAIKIN 使用独立 JSON 信封：`schema`、`model`、`variant`、`firmware`、`config_version`、`config`。不能把 MiCO 文件、普通 `full` 和 `hub` 备份混用。恢复先校验全部内容，再一次持久化；失败保留原设置。

<a id="m1-display-storage-v9"></a>

## M1 双路配置存储v9

双路显示配置追加在原v8负载尾部，旧配置前缀与 CO₂ 字段偏移不变。v8启动迁移保留普通配置、旧 CO₂、阈值、蜂鸣器、automation与revision；默认仍选legacy profile，新双路两位置为none、无RAM租期。只有显式新SET才启用dual，迁移不自动接管显示。

v8完整备份是明确的兼容例外：先校验原model/variant、v8精确长度、CRC及旧字段，再有界迁移到v9并初始化新尾段。v9备份继续要求v9精确长度与语义；未知未来版本拒绝。候选配置与profile同笔持久化，结果按下述提交边界判断；短期API数值和剩余租期不进入备份。

<a id="m1-display-storage-v10"></a>

## M1 格式显示存储 v10

v10 在现有两个 32 字节来源记录之后追加两个 presentation 记录，包含模式、标识/单位标志、九位灯掩码和保留字节。所有 v9 偏移、v8 前缀及网络/产品配置保持不动。原 display 级保留字节区分 dual=0、formatted=1；旧 v2 字段仍供 v2 使用，不能直接重解释为新格式标志。

先按冻结的 v2 规则验证 v9，再初始化追加的显示默认值，原子保存 v10；保留既有 legacy/dual profile、选择、revision 和其他配置，迁移本身不激活 formatted。既有 v8 启动和导入行为保留；只有成功的显式 `display_profile.set` 才激活格式显示。API 样本、解码运行值和租期仅在 RAM，不进入备份。

v8/v9 完整备份必须匹配各自历史原生长度及 padding、model/variant/schema/CRC 和历史字段语义，先在 RAM 转换再一次提交；v10 备份要求精确 v10 布局。畸形、跨变体或未来版本记录整笔拒绝，不接受部分配置；失败按下述提交边界处理。旧 v9 固件遇到 v10 必须进入既有“不支持布局”恢复路径，不能按改动偏移读取或静默覆盖配置。

<a id="storage-commit-results"></a>

## MiCO 存储提交结果

以下适用于采用事务存储修复的 TC1 / A1 / M1 开发实现。CAS冲突或 `busy` 在写入前拒绝候选。更新已有有效配置且可确认候选尚未提交时，`storage_error` 恢复旧 RAM 配置，并保留至少一份旧有效配置副本。

主分区完整内容和提交 CRC 尾记录均已确认后，配置已提交，返回 `accepted` 并保留新 RAM 配置；随后刷新第二副本失败不会把已提交配置报为失败，也不承诺此时双副本均健康。

若尾记录写入后持续读取失败，提交结果可能无法判断：仍返回既有 `storage_error` 并恢复旧 RAM 配置，但 Flash 可能是旧值或新值。设备锁定本次启动的后续写入，以 `migration_state=confirmation_required` 进入只读恢复模式并保留可读副本。普通 GET 读取 RAM，不能证明 Flash 已回滚。待重启并成功完成配置读取与必要的副本修复后，再独立 GET 核对 revision 和完整配置；不新增错误码或自动重写旧配置。

## 恢复模式

`config.get` 中的 `migration_state` 为 `ready` 或 `confirmation_required`；后者表示配置恢复模式，可能使用 RAM 默认值配网，也可能因上述提交结果不确定而保留旧 RAM 配置。需要清空原存储时仍须明确确认。恢复期间不能通过普通设置或自动任务覆盖原 Flash。

## 语言

设备 `config.get.language` 使用 `zh-CN` / `en`，默认 `zh-CN`。通过设备 `config.set` 的 `values.language` 修改，和名称设置一样持久化。

```json
{"request_id":"language_1","action":"config.set","params":{"values":{"language":"en"}}}
```

浏览器语言单独保存，可自动或手动选择。设备语言决定 MQTT Discovery 的传感器名称；切换后重新公告，实体 ID、主题、唯一标识和用户名保持稳定。配置备份保留设备语言。

## OTA 分流与依赖

v1 开发约定使用 `/ota/v1/<model>/<variant>/latest.json`。旧路径在正式桥接版本验收后固定到 v1.0.0，不持续向 v0.9.x 设备推送未来不兼容版本；分流上线是独立发布步骤。

OTA 选择必须同时核对机型、variant、签名和版本。DAIKIN `hub` 是独立中枢版本，不能由普通 `full` 自动跨变体升级。浏览器直接读取并校验发布差异；不可用时说明原因并要求额外确认。

声明 `ota_variant_conversion:"full-to-hub"` 的 DAIKIN `full` 固件可使用独立的[显式签名转换接口](device-http.md#daikin-full-hub)。普通签名/未签名 OTA 仍保持同 variant；转换不改分区表，且不支持 `hub` → `full`。

Wi-Fi 固件、传感器 MCU 和前端制品分别记录版本。固件使用完整提交与 SHA-256 固定的前端发布制品；构建或 UART 接收成功不代表新固件已经运行。
