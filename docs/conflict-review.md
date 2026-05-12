# 文档冲突审查

审查日期: 2026-05-09
审查范围: `team-speak-ai/docs/` 全部 7 个文档 vs 前后端实际代码

---

## A. 文档 vs 实现冲突 (3 项待定)

### A1. 未实现的逻辑节点类型

`node-system-design.md` 和 `view-mode-and-features-spec.md` 设计了以下逻辑节点，**全部未实现**：

| 节点 | 用途 | 计划 |
|---|---|---|
| `condition` | 条件分支 (if/else) | 未来规划 |
| `merge` | 合并 (wait_all/wait_any) | 未来规划 |
| `delay` | 延迟 | 未来规划 |
| `break` | 循环中断 | 未来规划 |
| `notify` | 通知 | 未来规划 |
| `loop` | 循环 | 未来规划 |
| `filter` | 过滤 | 未来规划 |

来源文档: `node-system-design.md`, `view-mode-and-features-spec.md`

- [ ] **A)** 标记为"未来规划"，文档中加注 [未实现]
- [ ] **B)** 删除这些设计，等需要时再重新设计
- [ ] **C)** 选择优先级高的开始实现（请注明哪些）

回复:


---

### A2. Flow Parameters + Start 节点 + 流程变量读写节点

| | 文档要求 | 实际实现 |
|---|---|---|
| 功能 | 流程参数管理 + $param 引用 + 专用读写节点 | 已完成设计，待实现 |

来源文档: `view-mode-and-features-spec.md`, `flow-variables-and-start-node.md`

- [x] 已完成详细设计 — 2026-05-09

设计文档: `docs/flow-variables-and-start-node.md`，包含：
- Start 节点（auto_run + init_params 写入流程参数）
- flow_var_read / flow_var_write 节点
- 流程参数管理面板（前端 UI）
- $param.xxx 保留机制
- 4 阶段实施计划


---

### A3. System Variables (`sys_var` 节点)

| | 文档要求 | 实际实现 |
|---|---|---|
| 功能 | 系统变量读写节点 + 持久化 + WS 命令 + 管理面板 | 已完成设计，待实现 |

来源文档: `view-mode-and-features-spec.md`, `flow-variables-and-start-node.md`

- [x] 已完成详细设计 — 2026-05-09

设计文档: `docs/flow-variables-and-start-node.md`，包含：
- sys_var_read / sys_var_write 节点
- SysVarManager（data/system_vars.json 持久化）
- sys_var.list/get/set/delete WS 命令
- 系统变量管理面板
- 阶段 4 实施计划


---

## B. 文档之间的冲突 (1 项待定)

### B1. 节点分类范围不一致

- `node-system-design.md` v2.1: 引入了 Logic 类（condition/merge/delay 等）和 Transform 类的 `sys_var`
- `architecture-spec.md`: 只描述了已有的节点类型

此冲突与 A1 合并处理。核心问题：**v2.1 设计是否作为当前实现目标？**

---

## C. 核心决策

> **`node-system-design.md` v2.1 的设计是否作为当前实现目标？**

- 如果 **是**: 需要实现 Logic 节点、sys_var、$param → 工作量大
- 如果 **否**: 将 v2.1 标记为未来规划，清理文档冲突，专注于当前已有功能的文档一致性

回复:

---

## D. 已解决项 (11 项)

| # | 冲突 | 解决方案 | 日期 |
|---|---|---|---|
| 1 | WebSocket 端点数量 | 删除 `/ws/pipeline`，保留 `/ws` + `/ws/teamspeak` | 2026-05-09 |
| 2 | `/ws/pipeline` 信封格式 | 随端点删除一并消除 | 2026-05-09 |
| 3 | `ConnectionDef.type` 连接类型 | 删除 `"trigger"`，统一为 `"data" \| "event"` | 2026-05-09 |
| 4 | 画布默认尺寸 | 统一为 2000x1500 | 2026-05-09 |
| 5 | `notification.list` 命令 | 实现完整支持（后端 JSONL 持久化 + 前端分页） | 2026-05-09 |
| 6 | `sidebar.js` Store | 已创建，从 AppLayout.vue 提取 | 2026-05-09 |
| 7 | `files.js` Store | 已创建并接入上传流程 | 2026-05-09 |
| 8 | 节点类型数量 | 删除固定数量描述，改为按需扩展 | 2026-05-09 |
| 9 | `connection.create` 类型校验 | 添加 type 白名单校验 | 2026-05-09 |
| 10 | 文档间连接类型不一致 (B1) | 随 A3 一并解决 | 2026-05-09 |
| 11 | WebSocket 协议覆盖范围 (B3) | 文档更新为双端点描述 | 2026-05-09 |
