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
