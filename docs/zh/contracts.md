# Schema 与样例

[English](https://phicomm-io.github.io/iotcloud-community-protocols/en/contracts/)

机器可读内容与正文一起审查。下载后可以在固件主机测试、前端或平台测试中复用；测试通过表示符合该样例与规则，不代表设备物理验收。

| 文件 | 内容 |
| --- | --- |
| [接口索引](contracts/registry.json) | 接口 ID、规范版本、状态、生产者/消费者和实现入口 |
| [CO₂ 传感器 Schema](contracts/schemas/sensor-co2-v1.schema.json) | 账户作用域传感器消息的 CO₂ 接入字段 |
| [来源配置 Schema](contracts/schemas/m1-co2-source-set-v1.schema.json) | 严格的 `co2_source.set` 参数 |
| [JSON 正反样例](contracts/examples/cases.json) | 类型、范围、单位、未知字段与嵌入 NUL 的边界 |
| [MCU 能力与操作定义](contracts/m1-uart-v1.json) | 帧长度、状态、能力偏移和通用显示操作码 |
| [UART 测试向量](contracts/vectors/m1-uart-v1.json) | 通用显示请求、查询和按钮事件 |

在仓库根目录运行：

```sh
python tools/validate.py
python tools/build.py
python tools/validate.py --consumer /path/to/implementation
```

消费者检查需要先检出 `protocols.lock.json` 指定的文档提交。Schema 校验不了的约束还需实现测试：主题与 ID 一致、同账户授权、样本新鲜度、序号重放、持久化回滚和 UART 调度。例如两个在 Schema 上合法的消息，仍可能因重复序号而被拒绝。
