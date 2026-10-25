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
