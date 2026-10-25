# 平台接口与大金中枢

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/platform-hub/)

本页的中枢接口状态为 **implemented-unreleased**：对应开发实现，尚未发布新的 v1 固件，也不代表 Apple Home 配对、物理输出或长期运行已经验收。接口索引中的 `firmware/` 路径对应 [固件仓库](https://github.com/phicomm-io/phicomm-community-firmware)，由实现仓库的 `protocols.lock.json` 固定本规范提交；交付时另记录实际实现提交。

## 管理平台接入面

共享前端使用 `apiOrigin` 和 `mqttWS`。账户 API 包括 `/api/auth/login`、`me`、`logout`、`password`、`mqtt-password`、`/api/devices` 和 `/api/integrations/bemfa`。云平台可使用 Cookie、Bearer 和跨域配置；以下中枢只提供同源 HTTP 与 Bearer 会话，不能套用云平台的 Cookie 或管理权限。

平台 HTTP 按 `Accept-Language` 选择 `en` / `zh-CN`，未指定或无法识别时默认 `zh-CN`；响应携带 `Content-Language` 和 `Vary: Accept-Language`。错误响应的 `error` 与成功响应的 `message` 是可翻译文本，稳定的 `code` / `message_key` 不随语言改变；成功响应可选附加 `message_key`。客户端按稳定字段判断结果，不匹配译文，也不翻译用户名、设备名等用户原文。

管理员 `GET /api/admin/verification-emails` 的 `records[]` 可附加 `detail_key`，例如 `verification.interrupted`、`verification.delivery_failed`、`e.66ba1c71fe55`；`detail` 按请求语言呈现，并兼容已有数据库中的中文记录。邮件状态、验证码字段和用户输入原文不因语言改变。实现见 `platform/backend/{main,util,i18n,verification_emails}.go`；这些平台接口扩展不改变 MQTT 载荷，也不要求中枢提供管理员入口。

HTTPS 页面不能直接连接中枢的 HTTP/WS。中枢前端由自身 `/iotcloud/` 提供，不包含邮箱注册、邮件发送、GitHub 登录、别名或管理员账户。`/api/auth/github/status` 和 `/api/banner` 返回 `enabled:false`。

## 本地账户与 HTTP 会话

中枢是独立的 `variant:"hub"`；普通 `full` 仍是传感器版本。首次先设置设备 Web 密码，再以设备 Basic `admin` 认证调用：

```http
POST /api/hub/setup
Content-Type: application/json

{"username":"local","password":"local-password"}
```

用户名为 3–32 个 ASCII 字母、数字或下划线，密码为 8–63 个 UTF-8 字节，不能含 NUL。只创建一个本地 owner，不导入云账户。已配置时返回 HTTP 409；Web 密码未设置时不能初始化。密码使用独立盐的 PBKDF2-HMAC-SHA256 校验值存储。配置保存失败返回 HTTP 503 `storage_error`，保留旧配置。

`POST /api/auth/login {username,password}` 返回账户对象，并在 `X-IotCloud-Session` 响应头返回 64 位十六进制 token；后续使用 `Authorization: Bearer <token>`。中枢不签发或读取会话 Cookie。最多四个内存会话，有效期自登录起 12 小时，重启即失效。账户对象含 `username`、`mqtt_username`、`aliases:[]`、`is_admin:false`、`hub:true`、`mqtt_password_separate`。已计入的登录/MQTT 密码失败共享五次失败、30 秒退避窗口。

HTTP 检查 Host 为设备 IP、AP IP 或 `daikin-<device_id>.local`；携带 Origin 的写操作必须匹配 `http://<Host>`，OPTIONS 不提供跨域放行。请求体最大 12288 字节，POST/PUT 使用 `application/json`。账户会话、设备 Web Basic 密码及上游云凭据属于独立认证域。

| 路径 | 方法、请求与行为 |
| --- | --- |
| `/api/register/status` | GET，无会话；`hub:true`、`setup_required`、`mqtt_uri`、`mqtt_ws_uri`，云注册 `enabled:false` |
| `/api/auth/me` | GET，本地 owner 会话 |
| `/api/auth/logout` | POST `{}`，撤销当前会话 |
| `/api/auth/password` | POST `{current_password,password}`，修改账户密码并撤销会话；未分离时同时更新 MQTT 密码 |
| `/api/auth/mqtt-password` | POST `{current_password,password}`，当前密码指账户密码；分离 MQTT 密码、断开 Broker 客户端，保留 HTTP 会话 |
| `/api/devices` | GET；POST `{mac,model,version:"v2"}`，服务端写入当前 owner 和 `status:"active"` |
| `/api/devices/<mac>` | DELETE，移除登记与关联 Bemfa 映射；最后一条映射删除时关闭 Bemfa |
| `/api/hub/bridge` | GET/PUT，显式上游路由，见下文 |
| `/api/integrations/bemfa` | GET/PUT/DELETE，巴法云映射 |
| `/api/hub/homekit` | GET/PUT，HAP 配置与状态 |
| `/api/hub/homekit/pairing` | DELETE `{"confirm":true}`，清除配对并安排重启 |

除说明的初始化/公开查询外，以上路径要求本地会话。错误以 `code` 判断：401 `unauthorized`、400 `invalid_params`、409 `conflict`、429 `hub_rate_limited`、503 `storage_error` 或 `busy`。注册设备最多 12 个，机型为 `a1`、`m1`、`tc1`、`daikin`；MAC 是非全零/全 f 的小写 12 位十六进制 ID。

## 本地 MQTT Broker

| 项目 | 开发实现 |
| --- | --- |
| TCP | `mqtt://<host>:1883` |
| WebSocket | `ws://<host>:9001/mqtt`，WebSocket 13，子协议 `mqtt` |
| MQTT | 3.1.1，必须 Clean Session、非空 client ID、用户名与密码；发布 QoS 0/1，订阅授予 QoS 0；不提供 TLS 或持久会话 |
| 认证 | 本地 owner 的 MQTT 密码；初始与账户密码相同，可独立修改 |
| 上限 | 8 连接；每连接 24 订阅；主题 256 字节；包/消息边界 8192 字节；retained 最多 128 条、总计 49152 字节 |
| 共享预算 | 接收 24576、遗嘱 4096、订阅字符串 8192 字节；超限拒绝或关闭连接，不保证离线投递 |

TMCP 发布/投递限于 `phicomm/v2/u_<用户名UTF8十六进制>/...`；通配订阅投递时仍检查实际主题。非 `phicomm/v2/` 主题对已认证 owner 开放，供 HA 与自定义路由使用。这里是一个账户的可信 LAN Broker，不提供逐设备凭据或按登记 MAC 的 ACL；登记/删除用于管理列表、Bemfa 和 HomeKit，不撤销同 owner 下其他 MQTT 客户端的命名空间权限。

支持受权限约束的 LWT、通配订阅及 retained。`/command`、`/set` 后缀的主题禁止 retained 发布/遗嘱。retained 重放只投递给订阅者，不产生新的转发事件。账户/MQTT 密码变更清除本地连接、遗嘱和 retained 状态。Broker、上游 MQTT Client 与 Bemfa Client 同时运行，上游凭据不授予本地登录权限。

## 显式上游转发

```json
{"enabled":true,"mqtt":{"host":"broker.lan","port":1883,"user":"upstream","password":"upstream-password"},"mappings":[{"direction":"out","local_topic":"home/local","remote_topic":"home/remote","retain":true,"allow_retained":false}]}
```

PUT 的 `enabled` 与 `mappings` 必填，最多八条；可选 `mqtt` 要求 `host`、`port`、`user`，`password` 省略则保留。GET 只返回 `password_set`。主题必须为具体主题，禁止 `+`、`#` 和 NUL。`in` 的唯一来源键为 remote topic，`out` 为 local topic；不能重复。TMCP local topic 必须属于 owner。

- `out`：本地/内部发布到上游；保留位为原发布 retained 与规则 `retain` 的交集。
- `in`：上游到本地；上游 retained 默认拒绝，只在 `allow_retained:true` 时允许；写入本地的保留位由规则 `retain` 决定。
- 任一端为 `/command` 或 `/set` 时，`retain`、`allow_retained` 均须为 false。
- 上游/Bemfa 注入的事件不再次向外转发；共享最多 16 条 topic+payload 摘要，按来源隔离，在五秒内抑制自身回声。该窗口不提供永久去重或恰好一次执行保证。

重连与 retained 重放不生成新的出站转发。新鲜度、账户匹配、重复路由和循环边界属于运行时校验，不能仅凭 JSON Schema 判定。

## Bemfa

PUT 使用 `enabled`、`mappings` 和启用时的 `api_key`。空字符串 `api_key` 表示保留已有密钥；GET 隐藏密钥并返回 `key_set`、`max_mappings:8`、`status`。DELETE 删除集成设置。映射引用已登记设备的完整 `{mac,model,version,status,username}`，最多八条；topic 和设备/通道不能重复。

| 设备/通道 | topic 后缀 | 命令 | 状态 |
| --- | --- | --- | --- |
| TC1 0–5 | `001` | `on` / `off` → `outlet.set` | 对应 `socket_states` |
| A1 0 风扇 | `003` | `on`、`off`、`on#1`–`on#4` → 20/50/75/100% | 以实际输出取最近档位 |
| A1 1 灯 | `002` | `on`、`off`、`on#1`–`on#100` → `light.set` 百分比 | 原始 0–255 亮度转为百分比 |

新风 A1 根据 `fresh_air_on`/`fresh_air_speed` 识别，使用 `fresh_air.set`；普通 A1 使用 `fan.set`。请求/设定速度不能替代 applied 输出。retained 命令被拒绝，命令要求来自本地/内部发布、20 秒内的在线设备状态。上游注入的 availability、state、result，无论是否 retained，都不能刷新本地在线依据或完成待确认命令。TMCP 使用独立随机 request ID；10 秒无匹配本地回执记 `device_timeout`。Bemfa 的 `connected`/`accepted` 只证明转发回执，不证明负载或风扇已动作。状态值变化或距同值上次转发超过 30 秒时，在下一次状态事件中上报。

## HomeKit HAP

当前提供可选 HAP Bridge，端口 51826，`protocol:"hap"`；**未提供 Matter 配网或设备服务**。

```json
{"enabled":true}
```

以上为 `PUT /api/hub/homekit` 的完整参数。成功 HTTP 202 `{"code":"accepted","restart_required":true}`；持久化失败保留配置与当前会话。GET 返回 `enabled`、`protocol`、`ready`、`code`、`paired`、`devices`、`port`。仅在存储健康、初始化完成且尚未配对时，向已登录 owner 返回 `setup_code` 与 `setup_uri`；失败或已配对时省略。`code` 可为 `disabled`、`ok`、`storage_error`、`identity_changed`、`invalid_params`、`restart_required`。

`DELETE /api/hub/homekit/pairing {"confirm":true}` 在尝试清除前停止 HAP。失败返回 503，继续禁用 HAP；成功返回 202 并重启。配对存储不属于普通配置备份。设备列表/账户身份改变会停止旧 HAP 服务并要求重启，旧会话不能继续控制已删除设备。

| 来源 | HAP 服务 |
| --- | --- |
| TC1 | 六个 Switch，名称仍为 Outlet 1–6；没有逐路负载插入检测，不提供 OutletInUse |
| A1 | Fan 与 LightBulb；新风变体控制独立新风风扇 |
| M1/大金 | 温度、湿度、CO₂、PM2.5；大金另有 PM10，按有效测量上报 |

只信任本地/内部发布；上游注入和 retained 重放不能确认 HomeKit 操作。设备状态 30 秒内可达，传感器样本总年龄小于 20 秒才可用。失效返回不可用，不填零。风扇/灯同批电源与档位只发送一次修改，显式 off 优先；`light.set` 的 `brightness` 为 0–100%，设备状态为 0–255。控制需匹配成功 TMCP 回执，再通过回执后的新状态/主动 `status.get` 结果确认 applied 状态，等待上限 2.5 秒；不会由请求值乐观更新状态。

配对区只在既定 4 MiB 双 OTA 布局未占用的尾部 `0x3d0000`–`0x3fffff` 使用私有标记与 NVS；不修改安装分区表、不擦默认 NVS、不初始化未知非空数据。初始化或运行中 NVS 读写/提交失败会关闭 HAP 监听和连接，禁止继续配对与控制。工厂重置可清除已识别但损坏的配对区；无法识别的尾部保留，普通配置重置不声称已清除未知数据。

上述布局是 `firmware/DAIKIN/partitions.csv` 的有线安装布局，每个应用槽 `0x1e0000`（1966080 字节）。原厂设备可能仍为 1.5 MiB 应用槽；当前约 1.91 MB 的 Hub HAP 开发镜像超过原厂槽，不能按该有线布局假定可普通 OTA。构建成功和文件上传均不能证明安装分区兼容，部署前必须核对设备实际分区。

本地 Hub API/MQTT 只接受本地 owner。设备主动配置的原有上游 TMCP 仍可管理中枢本机，包括 `config.set` / `system.reset`；这是另一处管理信任入口，不会获得本地 owner Bearer 会话。HAP 配对码仅在未配对且健康时由本地 owner GET 获取，不进入普通 state、config 或配置备份。

实现入口：`firmware/DAIKIN/include/hub_{service,broker,transport,relay,home}.h`、`firmware/DAIKIN/src/{hub,home,http}.inc`、私有 HomeSpan 适配。验证入口：`firmware/DAIKIN/tests/hub/` 与 `firmware/DAIKIN/tests/test_hub_mqtt.py`。机器参数定义及正反例见 [Schema 与样例](contracts.md)。主机测试、固件构建、Apple Home 配对及实机验收分别记录。
