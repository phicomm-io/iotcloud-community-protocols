# Schema 与样例

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/contracts/)

机器可读内容与正文一起审查。下载后可以在固件主机测试、前端或平台测试中复用；测试通过表示符合该样例与规则，不代表设备物理验收。

| 文件 | 内容 |
| --- | --- |
| [接口索引](contracts/registry.json) | 接口 ID、规范版本、状态、生产者/消费者和实现入口 |
| [CO₂ 传感器 Schema](contracts/schemas/sensor-co2-v1.schema.json) | 账户作用域传感器消息的 CO₂ 接入字段 |
| [来源配置 Schema](contracts/schemas/m1-co2-source-set-v1.schema.json) | 严格的 `co2_source.set` 参数 |
| [传感器提醒写入](contracts/schemas/m1-alarm-set-v1.schema.json) / [状态](contracts/schemas/m1-alarm-state-v1.schema.json) | 可选蜂鸣器开关、期望/实际读回与旧 MCU 未知状态 |
| [中枢规则](contracts/daikin-hub-v1.json) | 认证、端口、路由来源、时效与 HAP 存储边界 |
| [本地账户 Schema](contracts/schemas/hub-setup-v1.schema.json) | 首次本地 owner 初始化 |
| [上游路由 Schema](contracts/schemas/hub-bridge-set-v1.schema.json) / [Bemfa Schema](contracts/schemas/hub-bemfa-set-v1.schema.json) | 显式方向、retained 限制、机型/通道映射 |
| [HAP 配置](contracts/schemas/hub-homekit-set-v1.schema.json) / [清除配对](contracts/schemas/hub-homekit-reset-v1.schema.json) / [状态](contracts/schemas/hub-homekit-state-v1.schema.json) | 严格写入、显式清除确认和配对码可见条件 |
| [双路配置](contracts/schemas/m1-display-source-set-v2.schema.json) / [运行状态](contracts/schemas/m1-display-source-state-v2.schema.json) / [API 租期](contracts/schemas/m1-display-data-set-v2.schema.json) | 两路独立来源、整体选择、CAS、明确清除与 MCU 确认边界 |
| [通用 typed sensor](contracts/schemas/sensor-values-v1.schema.json) | 同账号真实数据、TC1功率与A1主风机百分比、固定单位和无效null |
| [双路 UART v3](contracts/m1-uart-v3.json) / [新向量](contracts/vectors/m1-uart-v3.json) | D13 schema2、独立21/22/23、旧scalar兼容；原v1文件保留 |
| [按键重置](contracts/m1-reset-v1.json) / [事务向量](contracts/vectors/m1-reset-v1.json) | 独立 `0x72` 帧、待决 ACK 匹配、保存失败重试、去重与冲突保护 |
| [JSON 正反样例](contracts/examples/cases.json) | 类型、范围、单位、未知字段与嵌入 NUL 的边界 |
| [MCU 能力与操作定义](contracts/m1-uart-v1.json) | 帧长度、状态、能力偏移、通用显示与传感器蜂鸣器操作码 |
| [UART 测试向量](contracts/vectors/m1-uart-v1.json) | 显示、按钮、OP `14` 请求/应答及能力兼容边界 |

在仓库根目录运行：

```sh
python tools/validate.py
python tools/build.py
python tools/validate.py --consumer /path/to/implementation
python tools/validate.py --sources /path/to/workspace
```

索引的 `repositories` 将 `firmware`、`mcu`、`frontend`、`platform` 映射到各 Git 仓库；`implementation` / `verification` 均为别名后的真实文件路径。`--sources` 在同名目录的工作区核对这些路径。消费者检查需要先检出 `protocols.lock.json` 指定的完整文档提交，并验证索引 SHA-256；实现提交和未提交补丁摘要另行记录。这里的开发路径不表示该能力已进入公开发布。

Schema 只约束结构及可表达的字段关系。固件字符串长度按 UTF-8 字节计算，Schema 的长度按字符计算；还须在入口校验 UTF-8 与字节上限。阈值 `yellow <= red`、主题与 ID 一致、同账户授权、路由/通道唯一、空密钥保留条件、样本新鲜度、序号重放、实际位图与期望一致、持久化回滚和 UART 调度均需实现检查。例如两个在 Schema 上合法的消息，仍可能因重复序号而被拒绝。UART 校验器读取声明的字段与条件，不复制 MCU 控制实现。

双路阈值对象使用声明式扩展 `x-orderedFields:["low","high"]` 表达严格 low<high；仓库 validator 在标准 JSON Schema 外执行此关系。只运行通用 JSON Schema 的消费者还须自行执行该关系。配置 revision、来源/单位匹配、API TTL不超过配置上限、数值缩放可表示范围与读回确认仍需运行时检查。v3 UART 校验同时验证原始向量及新向量，并检查既有帧布局和字段未被重新定义。

按键重置向量验证帧边界、schema、保留位、待决事务匹配、5 秒 ACK 边界和持久化去重模型。消费者仍须测试真实按键计时、500 ms 重发、Flash 提交、至少 1 秒 Wi-Fi EN 低电平及两颗 MCU 重启；通过合同检查不表示这些硬件行为已验收。
