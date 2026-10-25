# 设备 HTTP 与命令

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/device-http/)

以下为 Wi-Fi 固件的设备接口。管理平台的账户 API 使用独立的 `/api/auth/...`，见 [平台接口](platform-hub.md)。

## 接入

设备 WebUI 以同源 HTTP 访问。局域网管理端先读取 `info` / `capabilities` 并核对机型和能力。设备 HTTP 使用 Basic 认证，用户名 `admin`、密码为设备 Web 密码；浏览器跨域请求必须通过设备允许的 Origin 与预检。HTTPS 页面连接 HTTP 设备仍受浏览器混合内容限制。

| 方法与路径 | 含义 |
| --- | --- |
| `GET /api/v1/info` | 机型、固件与设备身份 |
| `GET /api/v1/status` | 状态快照 |
| `GET /api/v1/capabilities` | 当前功能和动作 |
| `GET /api/v1/config` | 公开配置和密码已设置标记，不返回明文密码 |
| `POST /api/v1/command` | 下文的 JSON 命令 |
| `GET /api/v1/config/backup` | 有密码时下载完整备份，返回二进制数据 |
| `POST /api/v1/config/restore` | 上传完整备份；成功接受后安排重启 |
| `POST /api/v1/ota/convert` | 仅声明转换能力的 DAIKIN `full`，显式签名转换为 `hub`；见下文 |
| `POST /api/v1/mcu/exchange` | 仅 M1，原始二进制 MCU 请求 / 应答，6–262 字节请求 |

各机型还可提供日志、调度、内存和传感器诊断；以具体机型实现及能力为准。旧版本可能缺少表中的新增入口。

## 命令信封

HTTP 和 TMCP 共用动作及 JSON 信封：

```json
{"request_id":"web_123","action":"co2_source.get","params":{}}
```

```json
{"request_id":"web_123","code":"ok","message":"操作成功","data":{"source":"local","device_id":"","double_click":"none","revision":0,"valid":false,"button_events_supported":false}}
```

调用方用 `request_id` 匹配结果，按稳定的 `code` 判断成功或错误；`message` 是可翻译文案。`ok` 表示查询成功，`accepted` 表示接受操作。错误如 `invalid_params`、`busy`、`unsupported`、`conflict` 不得作为成功处理。完整动作列表取设备 `capabilities.actions`。

## DAIKIN 分区诊断

支持此扩展的 DAIKIN 固件在状态对象中提供只读 `status.ota_partitions`；`status.get {}` 的命令应答位置为 `data.ota_partitions`。这是可选诊断字段，客户端须兼容其他机型或旧固件未返回该对象。

| 字段 | JSON 类型与含义 |
| --- | --- |
| `running` | 字符串或 null；当前运行应用分区的 label，无法取得时为 null |
| `running_size` | 非负整数；当前运行应用分区容量，单位字节；`running:null` 时为 0 |
| `next` | 字符串或 null；SDK 选择的下次 OTA 目标分区 label，无可用目标时为 null |
| `next_size` | 非负整数；该 OTA 目标分区容量，单位字节；`next:null` 时为 0 |
| `entries` | 对象数组；完整枚举设备实际安装分区表中 SDK 可见的应用和数据分区 |
| `entries[].label` | 字符串；分区 label |
| `entries[].type` / `entries[].subtype` | 非负整数；ESP-IDF 分区类型/子类型编号 |
| `entries[].address` | 非负整数；分区起始 Flash 字节偏移 |
| `entries[].size` | 非负整数；分区容量，单位字节 |

数值均为 JSON 十进制数字，不是十六进制字符串。分区名称、数量和容量来自设备已安装的分区表，独立于构建使用的 CSV；不能假定名称一定为 `app0` / `app1`。该对象不包含 Flash 内容或凭据，只描述现状，不切换 OTA 布局、不改写分区表，也不代表某个镜像已安装或适合写入。

实现入口：`firmware/DAIKIN/src/commands.inc` 的 `otaPartitionStatus()` 与 `state()`。

与 `free_memory` 同级的可选状态字段 `minimum_free_memory`（启动以来最低空闲堆）和 `max_free_block`（当前最大可分配连续堆块）均为以字节计的非负整数；客户端须兼容字段缺失。

## DAIKIN 显式 full → hub 转换

此接口属于未正式发布的开发扩展。仅支持转换的 `full` 固件在 `capabilities.get {}` 响应中声明 `data.ota_variant_conversion:"full-to-hub"`；未声明时不得尝试。能力声明不保证任意 Hub 镜像均能装入当前设备的实际 OTA 槽。

必须先设置本地设备 Web 密码，以该密码通过 Basic `admin` 认证，再向独立接口提交完整 `PHOTA001` 签名二进制文件：

```http
POST /api/v1/ota/convert
Authorization: Basic <base64(admin:设备Web密码)>
Content-Type: application/octet-stream
X-IoTCloud-Target-Variant: hub
X-IoTCloud-Confirm: full-to-hub

<完整 PHOTA001 签名二进制文件>
```

两个确认头的值必须精确匹配；不能使用本地 Hub owner 或上游账户会话代替设备 Basic 认证。设备当前配置必须健康，且没有进行中的 OTA、待处理命令或已安排的重启；配置恢复期间禁止转换。

设备使用实际下一 OTA 槽容量检查应用负载，不采用构建 CSV 的假定容量。应用前缀必须在固定偏移匹配 DAIKIN 硬件、项目与目标 `hub` 身份，不能通过搜索散落字符串识别镜像。擦除非运行槽前，先检查固定前缀并以可信密钥认证签名封套。完整接收后，从 Flash 读回整个暂存负载并校验签名覆盖的摘要，再读回并核对固定身份，全部通过后才选择新启动分区。

| 正反例 | 结果 |
| --- | --- |
| 已声明能力的 `full`，密码认证与确认头正确，健康且空闲，签名 Hub 镜像装得下且全部校验通过 | HTTP 202，`{"code":"accepted"}`；安排重启 |
| 设备未设置 Web 密码 | HTTP 403，`set_web_password_first` |
| 已设 Web 密码，但 Basic 认证缺失或错误 | HTTP 401，`unauthorized` |
| 确认头的值缺失或错误 | HTTP 400，`invalid_params` |
| 当前处于配置恢复 | HTTP 409，`migration_required` |
| 进行中的 OTA、待处理命令或已安排的重启 | HTTP 409，`busy` |
| 当前运行身份不能选择显式 Full-to-Hub 目标 | HTTP 409，`unsupported_conversion` |
| 镜像超过实际槽容量、缺失/错误签名、摘要或 Flash 读回不一致、固定身份不是目标 Hub | HTTP 400，`invalid_image`；不激活镜像 |
| 普通 `/api/v1/ota/upload` 或 `/api/v1/ota/upload-unsigned` 提交不同 variant，即使附带转换头 | HTTP 400，`invalid_image`；普通入口始终保持当前 variant |
| `hub` 请求转换为 `full` | Hub 不提供转换接口，普通接口拒绝跨 variant；Hub 大配置与 Full 不兼容 |

转换不改写分区表或普通配置，保留共用的 Wi-Fi、MQTT 和设备 Web 密码。首次 Hub 初始化仍须原设备 Web 密码，HAP 默认关闭；安装新镜像不等于已创建本地 owner 或完成 HomeKit 配对。转换也不扩大 OTA 槽：原厂 1.5 MiB 槽仍不能接受超出该容量的镜像。HTTP 202 只确认校验通过并安排重启；重新连接后，读取 `info` / `status` 的 `firmware_variant:"hub"` 才能确认 Hub 已运行。

## M1 CO₂ 来源

`co2_source.get {}` 返回：

| 字段 | 取值 |
| --- | --- |
| `source` | `local` 本机 SCD40；`mqtt` 本账户外部传感器 |
| `device_id` | 外部来源的小写 12 位十六进制 ID；本机为 `""` |
| `double_click` | `none` / `switch_display` |
| `revision` | 0..2147483647 的配置修订号 |
| `valid` / `ppm` | 新鲜度结果；无效时省略 `ppm` |
| `button_events_supported` | 传感器 MCU 是否声明扩展按键事件能力 |

修改使用 `co2_source.set`，四个配置字段必须完整，携带最近读取的 `revision`：

```json
{"request_id":"web_124","action":"co2_source.set","params":{"source":"mqtt","device_id":"123456abcdef","double_click":"switch_display","revision":0}}
```

禁止选择自身设备；`local` 必须清空 `device_id`。修订不匹配返回 `conflict`，成功返回递增后的配置。OTA、配置重启或 Wi-Fi 试连接占用时返回 `busy`；持久化失败不发布新配置。修改后清除旧来源缓存，等待新数据。

显示模式、替换位置、阈值和交替周期由 `co2_display.get` / `co2_display.set` 管理。显示开关不改变真实甲醛、PM 或 CO₂ 采样。MCU 来源与按钮规则见 [显示源](m1-display.md)。

## M1 传感器提醒

`alarm.get {}` 读取阈值和可选传感器蜂鸣器开关。`alarm.set` 必须包含 `sensor`（`hcho` / `pm25`）、`yellow`（整数 0..65535）、`red`（整数 1..65535 且不小于 `yellow`）、最近的 `revision`（整数 0..2147483647）；可选 `buzzer_enabled` 必须为 JSON 布尔值，只修改指定传感器，省略则保留原设置。禁止未知字段、字符串/浮点数冒充整数和数值冒充布尔值。

```json
{"request_id":"web_alarm_1","action":"alarm.set","params":{"sensor":"pm25","yellow":75,"red":150,"revision":0,"buzzer_enabled":false}}
```

成功持久保存后返回 `accepted` 及递增后的完整配置。修订不匹配、修订达到上限或运行时被占用返回 `busy`；存储失败返回 `storage_error` 并完整回滚。阈值单位保持 `main_controller_raw_u16`，不能根据传感器名称擅自换算。旧配置或未知扩展 schema 的两个期望蜂鸣器开关均按默认 OFF 迁移，保留原阈值和修订号。

| `alarm.get` 数据字段 | 含义 |
| --- | --- |
| `revision` | 当前配置修订号 |
| `hcho_configured` / `pm25_configured` | 对应阈值是否已配置 |
| `hcho_yellow` / `hcho_red` / `pm25_yellow` / `pm25_red` | 各传感器阈值 |
| `hcho_buzzer_enabled` / `pm25_buzzer_enabled` | 已持久保存的期望开关，默认 false |
| `buzzer_supported` / `mcu_alarm_schema` | MCU 能力是否支持，以及 0 / 1 schema |
| `buzzer_confirmed` | 新鲜独立读回与当前修订、期望位图均一致 |
| `buzzer_confirmation` | `mcu_readback` / `pending_mcu_readback` / `requires_mcu_upgrade` |
| `mcu_hcho_buzzer_enabled` / `mcu_pm25_buzzer_enabled` | 实际开关；未知或读回满 15 秒为 null |
| `mcu_buzzer_mask` | 实际 0..7 位图；未知为 null |
| `sensor_alarm_active` | MCU 最近轮询的传感器提醒条件；未知为 null，不表示实际声音检测 |
| `uart_sent` / `confirmation` | 兼容的阈值发送结果；`confirmation` 始终为 `uart_send_only` |
| `unit` | `main_controller_raw_u16` |

Wi-Fi 端先保存期望值，再按 MCU 能力发送 [OP `14`](m1-uart.md#op-14)，最后独立只读核对；写应答不产生 `buzzer_confirmed:true`。阈值 `uart_sent:true` 同样不代表蜂鸣器读回。旧 MCU 仍可保存期望设置，但 `buzzer_supported:false`、`buzzer_confirmation:"requires_mcu_upgrade"`，实际字段均为 null。客户端应保留“期望 OFF、实际未知”的区别，不宣称关闭成功。
