# IoTCloud 开发接口与协议

面向固件、传感器 MCU、WebUI 和管理平台开发者的接口定义、协议格式及兼容性约定。

[开发文档](https://phicomm-io.github.io/iotcloud-community-protocols/) · [English](https://phicomm-io.github.io/iotcloud-community-protocols/en/) · [项目主页](https://phicomm-io.github.io/)

- `docs/`：开发约定、设备 HTTP / MQTT 接口、M1 MCU 协议、平台与中枢。
- `contracts/`：版本化的接口索引、JSON Schema、正反样例及 UART 测试向量。
- `tools/`：协议校验和 Pages 构建工具。

v1 开发规范区分已实现接口和待实现草案。功能是否可用以设备能力查询和对应版本为准；文档版本独立于固件版本。

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/validate.py
.venv/bin/python tools/build.py
.venv/bin/python -m http.server 8000 --directory build/site
```

跨仓库变更先更新接口、样例和兼容性说明，再在实现 PR 中引用文档提交。各消费仓库以 `protocols.lock.json` 固定提交与接口索引校验值，流程见 [贡献规范](CONTRIBUTING.md)。`main` 自动发布 Pages，`dev` 和 `feature/*` 运行检查。

文档、协议定义及本仓库工具按 MIT 许可证提供。各实现仓库使用各自许可证。
