# 修改接口与协议

使用 `main` / `dev` / `feature/*` 工作流。通常从 `dev` 建功能分支，PR 合入 `dev`；完成核对后由 `dev` 合入 `main` 并发布文档。紧急修订使用 `hotfix/*`，合入 `main` 后同步 `dev`。

一次接口变更包含：

1. 使用范围、规范版本和状态：`implemented-unreleased`、`draft`、`released` 或 `deprecated`（需替代接口和原因）。发布状态需要填写可核对的实现版本。
2. 请求、响应、单位、范围、预留位、权限、时效、重试和错误行为。
3. 新旧实现的兼容策略，以及固件、MCU、前端、平台各自的变更链接。
4. 对应的 JSON Schema、正反样例或 UART 向量；更新中英文正文。

新增字段优先采用可选字段和能力协商。不要重新解释已分配的操作码、字段或主题。旧接收端允许忽略的响应扩展可以追加；配置写入仍需拒绝未知字段，防止拼写错误被静默接受。破坏性变更使用新的协议/schema 标识，并写明迁移与恢复行为。

`contracts/registry.json` 是跨仓库接口索引。接口定义尚未实现时标记 `draft`；已经存在的实现记录源码路径与验证入口，不将构建、自动化检查或文档发布视为实机验收。`repositories` 声明仓库别名，引用使用 `<别名>/<真实文件路径>`；在同名目录工作区运行 `python tools/validate.py --sources /path/to/workspace` 核对路径。交付时另外记录实现提交及未提交补丁摘要，不把可变分支链接当作固定版本证据。

消费仓库的 `protocols.lock.json` 格式为：

```json
{
  "schema": 1,
  "repository": "phicomm-io/iotcloud-community-protocols",
  "commit": "<40 位提交 SHA>",
  "registry_sha256": "<contracts/registry.json 的 SHA-256>",
  "contracts": ["tmcp-v2", "m1-display-v1"]
}
```

在本仓库检出该提交后，执行 `python tools/validate.py --consumer /path/to/consumer`，同时核对锁定提交、索引哈希和所引用接口。文档修订不会自动改变设备运行时协议。实现 PR 应注明所依据的规范提交、能力协商和测试结果。

运行 `python tools/validate.py`、`python tools/build.py` 和 `git diff --check`。不要提交生成的 `build/`，不要把凭据、真实账户或设备数据写入样例。
