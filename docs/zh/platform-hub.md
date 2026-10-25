# 平台接口与中枢草案

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/platform-hub/)

## 管理平台现有接口

现有前端通过可配置 `apiOrigin` 和 `mqttWS` 接入后端。HTTPS 页面不能连接不安全的 HTTP / WS 服务；局域网中枢可从自身 HTTP 地址提供同源前端。账户会话与设备 Web Basic 密码是不同的认证域。

| 路径 | 方法与用途 |
| --- | --- |
| `/api/auth/login` | POST `{username,password}`，成功返回账户对象 |
| `/api/auth/me` | GET 当前账户 |
| `/api/auth/logout` | POST 注销当前会话 |
| `/api/auth/password` | POST `{current_password,password}` 修改网站密码 |
| `/api/auth/mqtt-password` | POST 修改 MQTT 密码，按实现要求确认当前密码 |
| `/api/devices` | GET 设备列表；POST 登记设备 |
| `/api/devices/...` | PUT / DELETE 管理具体设备，按账户命名空间校验 |
| `/api/integrations/bemfa` | GET / PUT 巴法云转发设置 |

前端使用 `credentials:include`，同时支持 `Authorization: Bearer <token>`；登录响应 `X-IotCloud-Session` 提供会话 token。账户对象含 `username`、`mqtt_username`、`aliases`、`is_admin`；缺少可选字段时前端使用默认值。跨域部署需要显式允许来源；Cookie 写操作校验 Origin。错误以 `code` 为稳定标识，显示文案可按 `Accept-Language` 翻译。

此处列出共享接入面；完整云端账户生命周期由平台实现维护。中枢应复用前端需要的字段与响应格式，并明确声明不支持的云端能力。

## 大金中枢版本：草案，待实现

中枢使用独立 `variant:"hub"`，显示名称“中枢版本”。普通 `full` 继续用于传感器设备。以下是已确认的功能范围，端口、容量、转发配置结构和所有新增 API 须在实现前补齐 Schema 与测试，不能按草案当作现有功能调用。

- 独立本地账户，局域网设备和 HA 可连接的 MQTT TCP / WebSocket Broker，现有前端可登录管理。
- 本地账户与云账户独立；先不包含邮箱注册、邮件服务或 GitHub 登录。
- Broker 与上游 MQTT Client 同时运行，各自保持连接、权限、队列与重连状态。
- 按明确映射转发巴法云和上游事件，保留自身传感器上报。

## 跨仓库实现要求

本地 Broker 继续使用 [TMCP 账户命名空间](mqtt.md)，按连接认证确定账户。保留消息、遗嘱、通配订阅和 HA 发现投递均受账户权限限制；未经授权的账户不能读取其他设备或管理主题。设备登记、删除和账户禁用同步更新访问权限。

转发必须有显式方向、源和目标。不要把所有消息在 Broker 和上游之间无条件互相复制。规则需要定义事件身份、去重窗口、跳数/来源以及重连后的 retained 行为；命令和结果不能产生循环。连接数、最大包、订阅数、retained 总量、队列与超时均应有资源上限，达到上限时明确拒绝。

固件、前端、发布工具和文档共同识别 `hub`：构建矩阵、下载名称、OTA catalog、配置备份和恢复都校验 variant。完成同源账户登录、TCP / WS、HA、巴法云和上游并行场景后，再将接口状态从草案更新为已实现。
