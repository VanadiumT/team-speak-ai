# WebSocket 协议规范

> 前后端统一通信协议。稳定不变的核心契约。

---

## 1. 设计原则

1. **双端点分离** — `/ws` 流程管理 + 执行推送；`/ws/teamspeak` 语音桥接。不混用 REST
2. **信封模型** — 所有消息共用外层，`action` 字段路由
3. **命令/事件分离** — 前端发 `command`，后端回 `event` + 可选 `ack`
4. **flow_id 路由** — 一条连接多流程，后端按 `flow_id` 分发
5. **Binary frame 传文件** — 不走 base64，直传二进制帧
6. **后端持有全量数据** — 前端不存业务状态

---

## 2. 端点

| 端点 | 用途 | 连接方 |
|------|------|--------|
| `/ws` | 流程管理、节点编辑、配置持久化、执行控制、状态推送 | 前端 ↔ 后端 |
| `/ws/teamspeak` | 语音桥接（转发 Java 桥协议） | Java 桥 ↔ 后端（内部） |

---

## 3. 消息信封

### 3.1 Text Frame — 所有非文件消息

```json
{
  "msg_id": "uuid-v4",
  "flow_id": "string",
  "type": "command|event|ack|error",
  "action": "node.create",
  "params": {},
  "ts": 1714230000123
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `msg_id` | UUID v4 | 唯一标识，去重 + ack 关联 |
| `flow_id` | string | 路由到对应引擎实例 |
| `type` | enum | `command` / `event` / `ack` / `error` |
| `action` | string | 见 §4 动作列表 |
| `params` | object | 随 action 而异 |
| `ts` | int64 ms | 发送方时间戳 |

### 3.2 type 语义

| type | 方向 | 说明 |
|------|------|------|
| `command` | 前→后 | 请求执行操作 |
| `event` | 后→前 | 状态变更推送 |
| `ack` | 后→前 | 同步确认（ref_msg_id 关联） |
| `error` | 后→前 | 错误响应 |

### 3.3 Binary Frame — 文件数据块

```
Bytes 0-3:  msg_id 字节长度 (uint32)
Bytes 4-N:  msg_id (UTF-8)
Bytes N+1+: 文件二进制数据
```

关联 text frame（`file.upload_start`）在前，通过 `msg_id` 关联。

---

## 4. 动作列表

### 4.1 连接生命周期

| action | dir | 说明 |
|--------|-----|------|
| `node_types` | S→C | 连接建立后下发可用节点类型元数据 |
| `sidebar.tree` | S→C | 侧栏完整树结构 |
| `connection.status` | S→C | 连接建立时下发 + 状态变更时推送 |

连接建立后下行顺序：`node_types` → `sidebar.tree` → `connection.status`。

### 4.2 连接管理

| action | dir | 说明 |
|--------|-----|------|
| `ping` | C→S | 心跳（30s 间隔） |
| `pong` | S→C | 心跳响应 |
| `connection.status` | S→C | 服务状态变更推送 |

心跳超时 90s 断开。重连后前端 `flow.load` 恢复。

### 4.3 流程管理

| action | dir | params | 说明 |
|--------|-----|--------|------|
| `flow.list` | C→S | `{}` | 请求流程列表 |
| `flow.list_result` | S→C | `{flows: FlowSummary[]}` | 流程列表 |
| `flow.load` | C→S | `{}` | 加载当前流程 |
| `flow.loaded` | S→C | `{flow: FlowDef}` | 流程完整数据 |
| `flow.create` | C→S | `{name, group, icon}` | 新建 |
| `flow.created` | S→C | `{flow: FlowSummary}` | — |
| `flow.delete` | C→S | `{}` | 删除当前流程 |
| `flow.rename` | C→S | `{name}` | 重命名 |
| `flow.copy` | C→S | `{flow_id?, name?}` | 复制 |
| `flow.update` | C→S | `{canvas?, params?}` | 更新画布/参数 |
| `flow.update_group` | C→S | `{flow_id?, group}` | 移动分组 |
| `flow.create_group` | C→S | `{group_path}` | 创建分组 |
| `flow.rename_group` | C→S | `{old_path, new_path}` | 重命名分组 |
| `flow.delete_group` | C→S | `{group_path}` | 删除分组 |
| `flow.toggle_enabled` | C→S | `{flow_id?}` | 启用/禁用 |
| `flow.export` | C→S | `{flow_id?}` | 导出单个 |
| `flow.import` | C→S | `{data, overwrite?}` | 导入单个 |
| `flow.export_group` | C→S | `{group_path?}` | 导出分组 (ZIP base64) |
| `flow.import_group` | C→S | `{data_b64, group?}` | 导入分组 |

### 4.4 节点 CRUD

| action | dir | params | 说明 |
|--------|-----|--------|------|
| `node.create` | C→S | `{node_type, position: {x, y}}` | 创建节点 |
| `node.created` | S→C | `{node: NodeDef}` | — |
| `node.delete` | C→S | `{node_id}` | 删除节点 |
| `node.deleted` | S→C | `{node_id}` | — |
| `node.move` | C→S | `{node_id, position: {x, y}}` | 移动（dragend 发一次） |
| `node.moved` | S→C | `{node_id, position: {x, y}}` | — |
| `node.update_config` | C→S | `{node_id, config: {}}` | 更新配置（partial） |
| `node.config_updated` | S→C | `{node_id, config: {}}` | — |
| `node.rename` | C→S | `{node_id, name}` | 重命名 |

### 4.5 连线 CRUD

| action | dir | params | 说明 |
|--------|-----|--------|------|
| `connection.create` | C→S | `{from_node, from_port, to_node, to_port}` | 创建连线 |
| `connection.created` | S→C | `{connection: ConnectionDef}` | — |
| `connection.delete` | C→S | `{connection_id}` | 删除连线 |
| `connection.deleted` | S→C | `{connection_id}` | — |

后端校验：端口存在性、数据类型兼容、无环（DAG）。

### 4.6 执行控制

| action | dir | params | 说明 |
|--------|-----|--------|------|
| `pipeline.run` | C→S | `{}` | 启动管线 |
| `pipeline.started` | S→C | `{execution_id}` | — |
| `pipeline.completed` | S→C | `{execution_id}` | — |
| `pipeline.stop` | C→S | `{}` | 停止管线 |
| `pipeline.stopped` | S→C | `{execution_id}` | — |
| `node.trigger` | C→S | `{node_id}` | 手动触发节点 |
| `node.status_changed` | S→C | `{node_id, status, summary?, progress?, data?}` | 执行中状态推送 |

执行中拒绝编辑类 command，返回 `PIPELINE_RUNNING` error。

### 4.7 执行状态

| action | dir | 说明 |
|--------|-----|------|
| `node.status_changed` | S→C | 节点状态变更（pending→processing→completed/error） |
| `node.log_entry` | S→C | 节点日志（{node_id, level, timestamp, message}） |

### 4.8 配置持久化

| action | dir | 说明 |
|--------|-----|------|
| `config.save_default` | C→S | 保存节点默认配置 |
| `config.load_default` | C→S | 加载节点默认配置 |
| `config.default_loaded` | S→C | 返回默认配置 |

### 4.9 预设管理

| action | dir | 说明 |
|--------|-----|------|
| `preset.list` | C→S | 列出某类型预设组 |
| `preset.list_result` | S→C | 预设组 + 预设项列表 |
| `preset.create` | C→S | 创建预设项 |
| `preset.update` | C→S | 更新预设项 |
| `preset.delete` | C→S | 删除预设项 |

### 4.10 文件上传

| action | dir | 说明 |
|--------|-----|------|
| `file.upload_start` | C→S | 声明上传（filename, size, mime_type） |
| `file.upload_chunk` | S→C | 通知接收进度（upload_id, received, total） |
| `file.upload_complete` | S→C | 上传完成 |
| `file.upload_error` | S→C | 上传失败 |

Chunk 数据走 Binary Frame。256KB 每片，支持断点续传。服务端校验魔数。

### 4.11 通知

| action | dir | 说明 |
|--------|-----|------|
| `notification.list` | C→S | 获取通知列表（支持 cursor 分页） |
| `notification.list_result` | S→C | 通知列表 + 下一页 cursor |
| `notification.mark_read` | C→S | 标记已读 |

### 4.12 历史（撤销/重做）

| action | dir | 说明 |
|--------|-----|------|
| `history.undo` | C→S | 撤销 |
| `history.redo` | C→S | 重做 |
| `history.undo_state` | S→C | 栈状态（can_undo, can_redo） |

### 4.13 系统变量

| action | dir | 说明 |
|--------|-----|------|
| `sys_var.list` | C→S | 列出所有系统变量 |
| `sys_var.list_result` | S→C | 系统变量列表 |
| `sys_var.get` | C→S | 获取单个变量 |
| `sys_var.set` | C→S | 设置变量值 |
| `sys_var.delete` | C→S | 删除变量 |

系统变量跨流程持久化，存储在 `data/system_vars.json`。

---

## 5. 数据模型

### 5.1 节点 (NodeDef)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一标识 |
| `type` | string | 节点类型标识 |
| `name` | string | 显示名称 |
| `position` | `{x, y}` | 绝对坐标 |
| `config` | object | 节点配置（含 preset 引用、端口来源等） |

### 5.2 连线 (ConnectionDef)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一标识 |
| `from_node` | string | 源节点 ID |
| `from_port` | string | 源端口 ID |
| `to_node` | string | 目标节点 ID |
| `to_port` | string | 目标端口 ID |

type 由系统根据端口 data_type 自动判断（event → event 连线，其他 → data 连线）。

### 5.3 流程 (FlowDef)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一标识 |
| `name` | string | 显示名称 |
| `group` | string | 分组路径（`/` 分隔） |
| `icon` | string | Material Symbols 图标 |
| `canvas` | `{width, height}` | 画布尺寸 |
| `params` | object | 流程参数 (key-value) |
| `nodes` | NodeDef[] | 节点列表 |
| `connections` | ConnectionDef[] | 连线列表 |

### 5.4 流程摘要 (FlowSummary)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | — |
| `name` | string | — |
| `group` | string | — |
| `icon` | string | — |
| `node_count` | int | — |
| `updated_at` | ISO8601 | — |

### 5.5 节点类型元数据 (NodeTypeDef)

下发时包含完整端口、tab、默认配置，前端据此动态渲染。数据结构见[管线系统](./03-管线系统.md) §2 端口体系。

---

## 6. 连接管理

### 6.1 心跳

- 客户端每 **30s** 发送 `ping`
- 服务端 **90s** 无活动断开连接
- 连接建立后服务端依次下发 `node_types` → `sidebar.tree` → `connection.status`

### 6.2 重连

- 前端检测断开 → 自动重连
- 重连成功 → `flow.load` 恢复完整状态
- 重连期间 UI 显示"重连中"，不阻塞用户

### 6.3 编辑/执行互斥

- 流程执行中（status=running）→ 后端拒绝所有编辑类 command → 返回 `PIPELINE_RUNNING`
- 前端收到 `pipeline.started` → 进入只读
- 收到 `pipeline.completed` 或 `pipeline.stopped` → 恢复编辑

---

## 7. 配置保存策略

| 触发 | 策略 |
|------|------|
| 节点创建/删除/移动 | 即时保存 |
| switch/toggle/select 配置变更 | 即时保存 |
| text input/textarea | 500ms debounce |
| 端口拖动 | dragend 保存 |
| 保存默认配置 | 显式触发 |

撤销/重做栈上限 100 条。500ms 内同一 config 连续修改合并为一条。
