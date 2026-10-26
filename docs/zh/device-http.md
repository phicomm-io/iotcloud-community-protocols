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

<a id="hub-byte-addressable-heap"></a>

### 中枢可按字节访问的堆

支持此扩展的大金 `hub` 固件在状态对象的 `hub` 中增加三个可选、只读的非负 JSON 整数，`status.get {}` 响应中位于 `data.hub`。单位均为字节，统计范围为 ESP-IDF 组合能力 `MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT`，即内部且支持按字节读写的内存。

| `data.hub` 中的字段 | 含义 |
| --- | --- |
| `free_byte_heap` | 当前该能力范围的空闲堆总量 |
| `largest_byte_block` | 当前该能力范围可分配的最大连续块 |
| `min_byte_heap` | SDK 自启动以来的低水位统计，即符合条件的各内存区域最低空闲量之和 |

各区域的低水位可能发生在不同时刻，因此 `min_byte_heap` 不一定等于某一时刻最低的空闲总量。既有同级 `free_memory`、`minimum_free_memory` 和 `max_free_block` 保留原 ESP getter 语义，不是这些按能力统计字段的别名。旧固件或其他变体可能缺少 `hub` 或其中字段，客户端须兼容；其他机型不能直接套用这些 ESP32 含义。

见[固定实现](https://github.com/phicomm-io/iotcloud-community-firmware/blob/a555e6de08e40d44a4a6cf0896c7cc1581540f76/DAIKIN/src/commands.inc#L63-L67)、[SDK 堆参考](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/system/mem_alloc.html)与[中枢连接准入说明](platform-hub.md#hub-memory-diagnostics)。这些可选诊断不改变必需合同字段或消费者 pin。

### 复位原因

支持此诊断的大金固件可返回只读 `status.reset_reason`，在 `status.get {}` 响应中位于 `data.reset_reason`。它是 `unsigned(esp_reset_reason())` 提供的非负 JSON 整数，表示上次复位原因。旧固件可能省略该字段，缺失时表示此诊断不可用。

以下数字对应大金 ESP32 所用 ESP-IDF 4.4.7 的 `esp_reset_reason_t`，不是跨机型或跨 SDK 共用的复位原因枚举。无法识别的数值按未知诊断保留。见[官方 SDK 参考](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/system/system.html#reset-reason)与[固定版本枚举定义](https://github.com/espressif/esp-idf/blob/38eeba213aa695aabfd6d89aa9f5078dbe5a94c3/components/esp_system/include/esp_system.h#L41-L53)。

| 数字 | SDK 枚举 | 含义 |
| --- | --- | --- |
| 0 | `ESP_RST_UNKNOWN` | 原因无法确定 |
| 1 | `ESP_RST_POWERON` | 上电 |
| 2 | `ESP_RST_EXT` | 外部引脚复位，不适用于 ESP32 |
| 3 | `ESP_RST_SW` | 经 `esp_restart()` 触发的软件复位 |
| 4 | `ESP_RST_PANIC` | 异常或 panic |
| 5 | `ESP_RST_INT_WDT` | 中断看门狗 |
| 6 | `ESP_RST_TASK_WDT` | 任务看门狗 |
| 7 | `ESP_RST_WDT` | 其他看门狗 |
| 8 | `ESP_RST_DEEPSLEEP` | 从深度睡眠唤醒 |
| 9 | `ESP_RST_BROWNOUT` | 欠压复位 |
| 10 | `ESP_RST_SDIO` | SDIO 复位 |

实现见[大金状态诊断](https://github.com/phicomm-io/iotcloud-community-firmware/blob/508dfed3597bb64bdfb3f29e10f2ee46c90189c2/DAIKIN/src/commands.inc#L28)。此可选诊断不改变必需合同字段，消费者现有规范 pin 无需因此更新。

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

禁止选择自身设备；`local` 必须清空 `device_id`。修订不匹配返回 `conflict`，成功返回递增后的配置。OTA、配置重启或 Wi-Fi 试连接占用时返回 `busy`；请求失败时保留当前 RAM 配置，Flash 提交结果按[存储说明](configuration.md#storage-commit-results)判断。修改后清除旧来源缓存，等待新数据。

显示模式、替换位置、阈值和交替周期由 `co2_display.get` / `co2_display.set` 管理。显示开关不改变真实甲醛、PM 或 CO₂ 采样。MCU 来源与按钮规则见 [显示源](m1-display.md)。

<a id="m1-display_profile-api"></a>

## M1 display_profile API

增量契约 `m1-display-v3` 提供 `display_profile.get {}`、`display_profile.set` 和 `display_value.set`，通过 `capabilities.actions` 声明。需要 MCU 支持 formatted UART，不能仅凭 HTTP 版本认定 MCU 已升级。GET 返回 `schema:3`、配置和独立的 `runtime`；SET 使用既有共享 revision/CAS，提交完整配置，不带 `schema` 或 `runtime`：

```json
{
  "revision": 12,
  "selected_source": "user",
  "double_click": "switch_display",
  "lanes": [
    {
      "slot": 0, "source": "api", "device_id": "",
      "metric": "custom", "unit": "", "ttl_seconds": 20,
      "display": {"mode": "integer", "show_label": false, "show_unit": false},
      "color": {"mode": "fixed", "lamps": [
        {"red": false, "green": false, "yellow": false},
        {"red": false, "green": false, "yellow": false},
        {"red": false, "green": false, "yellow": false}
      ]}
    },
    {
      "slot": 1, "source": "mqtt", "device_id": "F0:E1:D2:C3:B4:A5",
      "metric": "fan_speed_percent", "unit": "%", "ttl_seconds": 15,
      "display": {"mode": "integer", "show_label": false, "show_unit": false},
      "color": {"mode": "thresholds", "low": 25, "high": 75}
    }
  ]
}
```

来源、metric 和配置的物理单位沿用 [schema2 规则](#m1-dual-display-api)，`decimals` / `scale` 替换为必填的 `display` 对象。[五种模式与每区域九段灯](m1-display.md#m1-display-v3) 用于本地/MQTT 数据转换；PM 仅允许 `integer`。固定灯色要求三个完整对象，阈值转换为 float32 后必须有限且仍 low<high，按缩放前的物理值比较。api 来源可以保留模式、物理单位元数据和配色配置，但这些字段不转换直接写入的显示帧。

MQTT ID 接受恰好 12 位十六进制或六组冒号分隔字节，允许大小写；先规范化为小写紧凑形式，再做本机 ID 检查和持久化，响应始终返回规范形式。非 MQTT 的 ID 必须为空。`co2_source.set` 同样增加输入规范化，定义于新 [v2 输入 schema](contracts/schemas/m1-co2-source-set-v2.schema.json)。既有 `display_source.set` 实现也宽松接收这些拼写；这是冻结 v2 契约之外的输入扩展，旧 schema 文件字节不变。

`display_value.set` 直接写一个显示区域。先显式保存 formatted 配置，并将该路来源设为 `api`；请求必须匹配最新 revision，TTL 不超过该路配置上限。`number` 是 0..999 的整数数字寄存器，`decimal`、`show_label`、`show_unit` 都是必填布尔值；PM 必须 `decimal:false`。`lamps` 按左、中、右提供完整数组，每个位置必须包含红、绿、黄三个布尔开关。写入不做缩放、取整、饱和或阈值配色。拒绝小数或越界 number、物理 `value` / `unit` 字段、标量 `color` 和未知字段。

```json
{"request_id":"raw_display_1","action":"display_value.set","params":{"revision":13,"slot":0,"ttl_seconds":15,"number":123,"decimal":true,"show_label":false,"show_unit":true,"lamps":[{"red":true,"green":false,"yellow":false},{"red":false,"green":true,"yellow":false},{"red":true,"green":false,"yellow":true}]}}
{"request_id":"raw_clear_1","action":"display_value.set","params":{"revision":13,"slot":0,"ttl_seconds":0}}
```

首条显示 `1.23` 和原生 mg/m³ 单位，隐藏甲醛标识，九段色灯完全按请求点亮。TTL0 仅接收 revision/slot/ttl_seconds，恢复该区域原始读数。API 数值只在 RAM 中生效，过期、离线或重启不能重放旧租期。认证、retained 命令拒绝和 request_id 去重沿用已有命令规则；相同 request_id 不续租。`accepted` 不等于 MCU 确认。

GET runtime 的 `profile` 为 legacy / dual / formatted。有效 api 路的 `value` 是实际显示读数（decimal 为 true 时 number/100，否则 number），可能包含 float32 表示误差；`unit` 为实际显示的原生单位（slot0 mg/m³、slot1 µg/m³），隐藏时为空。本地/MQTT runtime 仍保留原始物理值和单位。`number`、format 标志和三个对象组成的 `lamps` 表示精确编码输出。无效路的 value/number/format/lamps 为 null，剩余 TTL 为零；已确认清除与数值有效是不同状态。

配置 SET 后独立 GET，比对 revision 和完整配置；直接写入后比对原始 number/flags/lamps 与新鲜 TTL。确认必须先收到当前配置代次匹配的 OP25 选择 ACK，再分别 OP26 查询两路，匹配 formatted-active=1、来源选择和编码输出。只有 profile=formatted、MCU 支持且两路均确认，才允许全局 `confirmed:true`；legacy/dual 投影不能确认或生效。单独一次 query 或旧 v2 缓存不能证明 formatted 已被选择。

v2 生效时读取 v3 只投影配置，不保存或切换：PM→integer；甲醛 scale1000→milli，否则 decimals0/1/2→integer/decimal_1/decimal_2。旧固定颜色转为三位置统一灯色，旧合并标识决定转为两个布尔值。显式 v3 SET 才激活 formatted。formatted 生效时，v2 GET 返回禁用的旧版视图，保留当前共享 revision，两路不确认、不生效；显式 v2 SET 切回 v2。旧 CO₂ SET 切回 legacy，同时保留两种新配置。profile 与配置按[存储提交规则](configuration.md#storage-commit-results)同笔保存，[v10 迁移见此](configuration.md#m1-display-storage-v10)。

机器定义：[profile SET](contracts/schemas/m1-display-profile-set-v3.schema.json)、[profile GET](contracts/schemas/m1-display-profile-state-v3.schema.json)、[raw value SET](contracts/schemas/m1-display-value-set-v3.schema.json)。

<a id="m1-dual-display-api"></a>

## M1 双路用户显示 API

本节保留已发布 schema2 的 `display_source` / `display_data` 行为；formatted schema3 使用上方新动作。

开发合同 `m1-display-v2` 新增 `display_source.get {}`、`display_source.set` 和 `display_data.set`。动作出现在 `capabilities.actions` 才可调用；这不代表传感器 MCU 已支持双路。`mcu.version.get` 的 `display_source_schema` 为 2 或 0，`dual_display_source_supported` 表示双路支持；旧 `display_source_supported` 仍只表示 scalar schema 1。实际控制还须完成 [双路能力协商与读回](m1-display.md)。

`display_source.set` 全量替换两路持久配置，携带最近读取的 revision。slot0 是甲醛位，slot1 是 PM2.5 位，必须各出现一次。默认 selected_source=`original`、double_click=`none`；两路默认 source=`none`、device_id=`""`、metric=`custom`、unit=`""`、decimals=0、scale=1、ttl_seconds=20、color=`{"mode":"fixed","value":"off"}`。

```json
{"request_id":"display_cfg_1","action":"display_source.set","params":{"revision":0,"selected_source":"user","double_click":"switch_display","lanes":[{"slot":0,"source":"mqtt","device_id":"001122334455","metric":"power","unit":"W","decimals":2,"scale":1000,"ttl_seconds":15,"color":{"mode":"thresholds","low":100,"high":1000}},{"slot":1,"source":"api","device_id":"","metric":"custom","unit":"%","decimals":1,"scale":1,"ttl_seconds":10,"color":{"mode":"fixed","value":"green"}}]}}
```

| 配置字段 | 规则 |
| --- | --- |
| `revision` | 严格 JSON 整数 0..2147483647，CAS；成功后递增 |
| `selected_source` | `original` / `user`，两路整体选择 |
| `double_click` | `none` / `switch_display`；闹钟响铃时优先取消闹钟，本次不切显示 |
| `lanes[].source` | `none` / `local` / `mqtt` / `api`；none 的位置始终原始 |
| `device_id` | mqtt 必须是本账户外部设备的小写 12 位 hex ID且非自身；其余为空 |
| `metric` / `unit` | 下表的固定组合；custom 仅 api 或 none，none 必须 custom+空单位 |
| `decimals` / `scale` | 整数 0..2 / 1或1000；按 `value / scale` 显示，不改变物理单位或告警 |
| `ttl_seconds` | 整数 1..60；最大数据寿命，物理源还受更严格的新鲜度限制 |
| `color` | fixed 模式必须 value=off/red/green/yellow；thresholds 模式必须有限 low<high，按缩放前物理值判断绿/黄/红 |

| metric | unit | 来源与范围 |
| --- | --- | --- |
| `temperature` | `°C` | local/mqtt/api；物理值 -40..125，负值无法在通用位置表示，回退原始 |
| `humidity` | `%` | local/mqtt/api；0..100 |
| `pm25` / `formaldehyde` | `µg/m³` / `mg/m³` | local/mqtt/api；有限非负 |
| `co2` | `ppm` | local/mqtt/api；1..65535，local 需真实 SCD40 能力 |
| `pressure` | `Pa` | local/mqtt/api；有限非负，centi-Pa/hPa 必须换算数值后才用 Pa |
| `power` / `energy` | `W` / `kWh` | mqtt/api；有限非负，TC1 当前新增 feed 仅 power，不宣称 energy |
| `tvoc` / `pm10` | `ppb` / `µg/m³` | mqtt/api；有限非负，以实际 producer 字段为准 |
| `fan_speed_percent` | `%` | mqtt 的 A1 或 api；有限0..100，A1 当前生效主风机输出百分比，非实测 RPM；fresh-air 变体仍为主风机 |
| `custom` | 白名单 | 仅 api；unit 为 `""`、`°C`、`%`、`µg/m³`、`mg/m³`、`ppm`、`Pa`、`W`、`kWh` 或 `ppb` |

local 指本机 M1，只允许温湿度、PM2.5、甲醛、CO₂、压力；没有传感器能力或新鲜样本时无效。mqtt 只消费同账号 [typed feed](mqtt.md#sensor-values-v1)，不接受任意 topic/URL/JSONPath。source=none 只允许 custom+空单位，不成为写入入口。未知字段、错误类型、单位不匹配、重复位置和 low>=high 均拒绝。

每路只有三位非负数字。数值编码须落在0..999，否则仅该路回退；原气体/单位段是否显示由固件按真实位置、metric、单位及 scale1 推导。玻璃没有可选择的 W、℃、% 等单位字形，客户端须明确逻辑单位与倍率，见[表示边界](m1-display.md#display-representation)。

`display_data.set` 仅向 source=api 的位置写入短期 RAM 数据，必须匹配当前配置 revision、unit，且 TTL 不超过该路上限；可选 color 在本条租期内直接指定。正常写入需要 value、unit 和1..60秒 TTL。立即清除使用独立形状，不以伪零表示缺失：

```json
{"request_id":"display_value_1","action":"display_data.set","params":{"revision":1,"slot":1,"value":45.6,"unit":"%","ttl_seconds":10,"color":"yellow"}}
{"request_id":"display_clear_1","action":"display_data.set","params":{"revision":1,"slot":1,"ttl_seconds":0}}
```

两者均沿用 HTTP Basic 或已授权 MQTT 命令认证，retained 命令拒绝；重复 request_id 返回原结果，不延长租期。公开 sensor 字段不能写入 API lane。新值和租期不写 Flash，重启不重放。`accepted` 只表示配置或租期操作已接受，不表示屏幕已确认。

GET 的配置字段仍在根：revision、selected_source、double_click、lanes；另有只读 `runtime`，禁止把 runtime 回写 SET：

| runtime 字段 | 含义 |
| --- | --- |
| `profile` | `legacy` / `dual`，当前调度策略 |
| `selected_source` | 包含双击 RAM override 的实际 original/user 选择；持久配置或重启会重建它 |
| `mcu_supported` | 明确协商双路 schema2；不是仅有 scalar 支持 |
| `confirmed` / `confirmation` | 新鲜独立 MCU 读回匹配；`mcu_readback` / `pending_mcu_readback` / `requires_mcu_upgrade` |
| `lanes[].slot/valid/value/unit` | 对应位置的来源结果；未知/无效 value 为 null |
| `age_ms` / `remaining_ttl_seconds` | 样本年龄或 null；剩余0..60秒 |
| `effective` / `reason` | 当前是否具备用户覆盖资格；reason为ok/disabled/missing/stale/offline/invalid/out_of_range/unsupported |
| `number/format/color` | 实际编码或 null；color 使用字符串枚举 |
| `confirmed` | 该路与独立 MCU 查询一致，不是 LCD 光学回读 |

全局 `confirmed` 仅在 `profile=dual`、MCU 支持且两路 `confirmed` 均为 true 时为 true，此时 `confirmation=mcu_readback`。已确认的清除状态可以是 `valid=false`、剩余租期 0；有效数值与确认状态分别表达。

`valid=true` 时数值、年龄和编码字段完整、剩余租期为正且 `reason=ok`；否则数值与编码字段为 null、剩余租期为 0。`effective=true` 还要求本路 MCU 读回已确认。

配置保存后独立 GET 核对 revision 和完整配置；数值写入后再 GET 核对该路 valid/value/unit/租期，MCU 确认仍须独立 UART 查询。旧 MCU 可保留 desired 配置，但不得声称双路已生效。失效不改持久选择，仅恢复对应原始读数；没有可靠离线事件时按 TTL 失效，不伪造 offline 判断。

成功的新 SET 持久选择 dual；成功旧 CO₂ SET 选择 legacy并保留双路配置。profile 与配置同笔保存；CAS冲突或busy不提交候选配置。`accepted` / `storage_error` 遵循[存储提交结果](configuration.md#storage-commit-results)，不能仅凭 `storage_error` 断言 Flash 已回滚。两路配置追加到 M1 存储v9，v8迁移与备份兼容见[配置说明](configuration.md#m1-display-storage-v9)。

## M1 传感器提醒

`alarm.get {}` 读取阈值和可选传感器蜂鸣器开关。`alarm.set` 必须包含 `sensor`（`hcho` / `pm25`）、`yellow`（整数 0..65535）、`red`（整数 1..65535 且不小于 `yellow`）、最近的 `revision`（整数 0..2147483647）；可选 `buzzer_enabled` 必须为 JSON 布尔值，只修改指定传感器，省略则保留原设置。禁止未知字段、字符串/浮点数冒充整数和数值冒充布尔值。

```json
{"request_id":"web_alarm_1","action":"alarm.set","params":{"sensor":"pm25","yellow":75,"red":150,"revision":0,"buzzer_enabled":false}}
```

成功持久保存后返回 `accepted` 及递增后的完整配置。修订不匹配、修订达到上限或运行时被占用返回 `busy`；存储失败返回 `storage_error`，其可确认故障与提交结果不确定的区别见[存储说明](configuration.md#storage-commit-results)。阈值单位保持 `main_controller_raw_u16`，不能根据传感器名称擅自换算。旧配置或未知扩展 schema 的两个期望蜂鸣器开关均按默认 OFF 迁移，保留原阈值和修订号。

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
