# 文档冲突审查

审查日期: 2026-05-09
审查范围: `team-speak-ai/docs/` 全部 7 个文档 vs 前后端实际代码

---

## A. 文档 vs 实现冲突 (3 项待定)

### A1. 未实现的逻辑节点类型

`node-system-design.md` 和 `view-mode-and-features-spec.md` 设计了以下逻辑节点，**全部未实现**：

| 节点 | 用途 |
|---|---|
| `condition` | 条件分支 (if/else) |
| `merge` | 合并 (wait_all/wait_any) |
| `delay` | 延迟 |
| `break` | 循环中断 |
| `notify` | 通知 |
| `loop` | 循环 |
| `sys_var` | 系统变量 (读/写/更新) |
| `filter` | 过滤 |

来源文档: `node-system-design.md`, `view-mode-and-features-spec.md`

- [ ] **A)** 标记为"未来规划"，文档中加注 [未实现]
- [ ] **B)** 删除这些设计，等需要时再重新设计
- [ ] **C)** 选择优先级高的开始实现（请注明哪些）

回复:


---

### A2. Flow Parameters (`$param.xxx`)

| | `view-mode-and-features-spec.md` 要求 | 实际实现 |
|---|---|---|
| 功能 | 用户自定义 key-value 存储在 Flow JSON `params` 字段，节点配置中通过 `$param.xxx` 引用 | **完全未实现** |

来源文档: `view-mode-and-features-spec.md`

- [ ] **A)** 实现此功能
- [ ] **B)** 标记为未来规划

回复:


---

### A3. System Variables (`sys_var` 节点)

| | `view-mode-and-features-spec.md` 要求 | 实际实现 |
|---|---|---|
| 功能 | `sys_var` 节点 + `data/system_vars.json` + `sys_var.list/get/set` WS 命令 + 系统设置面板 | **完全未实现** |

来源文档: `view-mode-and-features-spec.md`

- [ ] **A)** 实现此功能
- [ ] **B)** 标记为未来规划

回复:


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
