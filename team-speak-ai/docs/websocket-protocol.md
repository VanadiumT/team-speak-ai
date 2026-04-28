# TeamSpeak AI WebSocket 协议规范

> 前后端统一通信协议。单一 `/ws` 端点承载全部交互。

---

## 1. 设计原则

1. **单一连接** — 一个 WebSocket 承载流程管理、节点编辑、文件上传、配置持久化、执行状态推送，不再混用 REST API。
2. **信封模型** — 所有消息共用外层信封，`action` 字段路由到具体处理器。
3. **命令/事件分离** — 前端发 `command`，后端回 `event` + 可选 `ack`。
4. **`flow_id` 路由** — 一条连接可操作多个流程，后端按 `flow_id` 分发到对应引擎实例。
5. **Binary frame 传文件** — 大文件不分片为 base64，直接走 WebSocket binary frame。
6. **所有数据归属后端** — 节点坐标、连线、配置、侧栏结构全部存储于后端。

---

## 2. 端点

| 环境 | URL |
|---|---|
| 开发 | `ws://localhost:8000/ws` |
| 生产 | `wss://{host}/ws` |

Vite 代理配置（`vite.config.js`）：
```js
proxy: {
  '/ws': {
    target: 'ws://localhost:8000',
    ws: true,
  },
}
```

---

## 3. 消息信封

### 3.1 JSON 消息（Text Frame）

所有非文件数据的消息均为此格式：

```json
{
  "msg_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "flow_id": "darkzone_championship",
  "type": "command",
  "action": "node.create",
  "params": {
    "node_type": "ocr",
    "position": { "x": 40, "y": 300 }
  },
  "ts": 1714230000123
}
```

### 3.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `msg_id` | UUID v4 (string) | 是 | 消息唯一标识，用于去重和 `ack.ref_msg_id` 回执关联 |
| `flow_id` | string | 是 | 流程 ID。后端据此路由到对应的 PipelineEngine 实例 |
| `type` | enum | 是 | `"command"` / `"event"` / `"ack"` / `"error"` |
| `action` | string | 是 | 动作名，见 [§4 动作列表](#4-动作列表) |
| `params` | object | 否 | 动作参数，schema 因 action 而异 |
| `ts` | int64 (ms) | 是 | 发送方时间戳 |

### 3.3 type 语义

| type | 方向 | 说明 |
|---|---|---|
| `command` | 前端 → 后端 | 请求执行操作 |
| `event` | 后端 → 前端 | 状态变更推送（可能是 command 的结果，也可能是服务端主动推送） |
| `ack` | 后端 → 前端 | 对 command 的同步确认（`ref_msg_id` 关联） |
| `error` | 后端 → 前端 | 错误响应（`ref_msg_id` 可关联原 command） |

### 3.4 Binary Frame（文件数据块）

```
┌──────────────────────────────────────┐
│  Bytes 0-3:  msg_id 字节长度 (uint32) │
│  Bytes 4-N:  msg_id (UTF-8)          │
│  Bytes N+1+: 文件二进制数据           │
└──────────────────────────────────────┘
```

关联的 text frame 消息（`file.upload_start`）在前，binary frame 在后，通过 `msg_id` 关联。

---

## 4. 动作列表

### 4.1 连接生命周期

连接建立后，后端立即下发元数据。连接期间持续推送内部链路状态。

| action | dir | params | 说明 |
|---|---|---|---|
| `node_types` | S→C | `{types: NodeTypeDef[]}` | 连接建立后立即下发，告知可用节点类型 |
| `sidebar.tree` | S→C | `{groups: SidebarGroup[]}` | 侧栏完整树结构 |
| `connection.status` | S→C | `{services: ServiceStatus[]}` | 连接建立时下发 + 状态变更时推送 |

**`ServiceStatus`：**
```json
{
  "services": [
    {
      "id": "ts_bot",
      "name": "TeamSpeakBot 服务",
      "status": "connected",
      "detail": "ws://localhost:8080/teamspeak/voice",
      "since": "2026-04-28T14:20:00Z"
    },
    {
      "id": "backend",
      "name": "TeamSpeakAI 后端",
      "status": "healthy",
      "detail": "0.1.0"
    },
    {
      "id": "pipeline",
      "name": "Pipeline",
      "status": "listening",
      "detail": "STT 监听中"
    }
  ]
}
```

**`status` 枚举：**

| status | 含义 | 前端渲染 |
|---|---|---|
| `"connected"` | 已连接 | 绿色点 + 脉冲 |
| `"healthy"` | 运行正常 | 绿色点 |
| `"listening"` | 监听/运行中 | 蓝色点 + 脉冲 |
| `"connecting"` | 重连中 | 黄色点 + 脉冲 |
| `"disconnected"` | 断开 | 红色点 |
| `"error"` | 异常 | 红色点 + 脉冲 |

**推送时机：**
- `connection.status` 在连接建立后立即下发（当前全量状态）
- 任一 service 状态变更时，后端主动推送 `connection.status`（仅变更项，前端合并）
- `ts_bot` 状态在后端与 Java Voice Bridge 的重连/断连时变更
- `pipeline` 状态在执行启动/完成/listener 循环时变更

**前端渲染：** 底部状态栏，每项 = 状态点 + 标签 + 值，最多展示 3 项。

---

**`NodeTypeDef`：**
```json
{
  "type": "stt_listen",
  "name": "STT 持续监听",
  "icon": "mic_external_on",
  "color": "primary",
  "default_config": {
    "engine": "sensevoice",
    "keywords": ["求助", "集合", "撤退"],
    "sample_rate": 16000
  },
  "tabs": [
    { "id": "config",   "label": "配置" },
    { "id": "detail",   "label": "详情" },
    { "id": "log",      "label": "日志" },
    { "id": "fulltext", "label": "全文" }
  ],
  "ports": {
    "inputs": [
      {
        "id": "stt-in",
        "label": "音频帧 (PCM 16bit)",
        "data_type": "audio",
        "position": { "side": "left", "top": 30 }
      }
    ],
    "outputs": [
      {
        "id": "stt-out",
        "label": "识别文本 (String)",
        "data_type": "string",
        "position": { "side": "right", "top": 55 }
      }
    ]
  }
}
```

**`NodeTypeDef` 字段说明：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | string | 节点类型标识符，创建时传入 |
| `name` | string | 显示名 |
| `icon` | string | Material Symbols 图标名 |
| `color` | string | 主题色: `"primary"` / `"secondary"` / `"tertiary"` / `"outline"` |
| `default_config` | object | 创建新节点时的初始配置 |
| `tabs` | TabDef[] | 节点内标签页定义（顺序即渲染顺序） |
| `ports` | PortsDef | 输入/输出端口定义 |

**`TabDef`：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | tab 标识，前端生成 `#tab-{node_id}-{id}` 锚点 |
| `label` | string | 显示文字（如"配置"/"详情"/"日志"/"全文"） |

**标签页 id 约定：**

| id | 含义 | 前端渲染内容 |
|---|---|---|
| `config` | 配置 | 当前节点的可编辑参数表单（引擎选择、关键词列表、temperature 等） |
| `detail` | 详情 | **节点的核心交互区**，根据 `node.type` + `node.status` 动态渲染不同组件 |
| `log` | 实时日志 | 滚动日志区，接收 `node.log_entry` 实时追加 |
| `fulltext` | 全文 | 仅文本密集型节点，展示累积的完整文本（如 STT 全部记录、LLM 完整回复） |

> **`detail` 是节点的核心交互层。** 它不是被动展示 I/O 数据，而是根据节点当前状态渲染对应的交互组件——详见下方 §4.1.1。

> **注意：** 不是所有节点都需要全部 tab。例如 `input_image` 节点 `tabs: []`（无 tab，整个 body 就是上传界面），`ts_output` 节点也 `tabs: []`。

**`PortDef`：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 端口标识符（连线时引用） |
| `label` | string | 端口悬停提示文字 |
| `data_type` | string | 数据类型: `"image"` / `"audio"` / `"string"` / `"string_array"` / `"messages"` / `"event"` |
| `position.side` | string | `"left"`（输入）或 `"right"`（输出） |
| `position.top` | number | 相对于节点卡片顶部的像素偏移 |

> **端口渲染规则：** 前端根据 `position.side` 将端口放在节点左侧或右侧，根据 `position.top` 设置垂直偏移。输入端口挂在 `left: -7px`，输出端口挂在 `right: -7px`。

#### 4.1.1 前端如何根据后端数据渲染节点

前端不需要硬编码每个节点的 UI 细节。渲染由三要素决定：

**公式：`node.type` + `node.status` + `NodeTypeDef.tabs` → 确定渲染内容**

```
后端下发 NodeTypeDef                   前端本地组件注册表
┌──────────────────────┐              ┌─────────────────────────────┐
│ type: "input_image"  │──────────────→│ InputImageNode.vue         │
│ status: "pending"    │   查找组件     │  └─ 渲染: 文件拖拽上传区    │
│ tabs: []             │              │                             │
│                      │              │ InputImageNode.vue         │
│ status: "completed"  │──────────────→│  └─ 渲染: 已上传文件信息    │
└──────────────────────┘              └─────────────────────────────┘
```

**机制：**

| 层 | 负责方 | 内容 |
|---|---|---|
| 组件注册表 | 前端硬编码 | `{ "input_image": InputImageNode, "ocr": OcrNode, ... }` — 每种 type 对应一个 Vue 组件 |
| 状态分支 | 前端组件内 | 组件内部 `v-if` / `v-switch` 根据 `node.status` 决定渲染什么子界面 |
| 数据结构 | 后端下发 | `node.config`（可编辑配置）、`node.data`（运行时产物）、`node.status`（当前阶段） |

**`detail` tab 的状态→UI 映射表：**

| node.status | input_image | stt_listen | llm | ocr | 通用 |
|---|---|---|---|---|---|
| `pending` | 文件拖拽上传区 | "等待音频流..." | "等待上游上下文..." | "等待图片..." | 等待提示 |
| `processing` | 上传进度条 | 实时识别文本 + 关键词点亮 + 脉冲动画 | 流式文本 (StreamingText) + 光标闪烁 | 识别进度 | spinner / 进度条 |
| `completed` | 文件名、大小、预览 | 触发关键词高亮、完成提示 | 完整回复 (TextDisplay) + reasoning | OCR 文本展示 | 输出数据面板 |
| `error` | "上传失败：xxx" | "STT 错误：xxx" | "LLM 超时：xxx" | "OCR 错误：xxx" | 错误面板 (ErrorDisplay) |

**即使无 tab 的节点（如 `input_image`，`tabs: []`），整个节点 body 区域就是它的 `detail` 区**，直接根据 status 渲染对应组件。

> **关键原则：** 后端决定"这个节点是什么类型、当前什么状态、配置是什么"，前端决定"这种类型+这种状态应该渲染成什么样"。后端不关心前端的组件实现，前端不存储业务数据。

---

### 4.2 流程管理

| action | dir | params | 响应事件 |
|---|---|---|---|
| `flow.list` | C→S | `{}` | `flow.list_result` |
| `flow.list_result` | S→C | `{flows: FlowSummary[]}` | — |
| `flow.load` | C→S | `{}` | `flow.loaded` |
| `flow.loaded` | S→C | `{flow: FlowDef}` | — |
| `flow.create` | C→S | `{name, group, icon}` | `flow.created` |
| `flow.created` | S→C | `{flow: FlowSummary}` | — |
| `flow.delete` | C→S | `{}` | `flow.deleted` |
| `flow.deleted` | S→C | `{flow_id}` | — |
| `flow.rename` | C→S | `{name}` | `flow.renamed` |
| `flow.renamed` | S→C | `{flow_id, name}` | — |

**`FlowSummary`：**
```json
{
  "id": "darkzone_championship",
  "name": "暗区锦标赛",
  "group": "game_features",
  "icon": "sports_esports",
  "node_count": 9,
  "updated_at": "2026-04-28T14:23:00Z"
}
```

**`FlowDef`** 定义见 [§5 数据模型](#5-数据模型)。

---

### 4.3 节点 CRUD

| action | dir | params | 响应事件 |
|---|---|---|---|
| `node.create` | C→S | `{node_type, position: {x, y}}` | `node.created` |
| `node.created` | S→C | `{node: NodeDef}` | — |
| `node.delete` | C→S | `{node_id}` | `node.deleted` |
| `node.deleted` | S→C | `{node_id}` | — |
| `node.move` | C→S | `{node_id, position: {x, y}}` | `node.moved` |
| `node.moved` | S→C | `{node_id, position: {x, y}}` | — |
| `node.update_config` | C→S | `{node_id, config: {}}` | `node.config_updated` |
| `node.config_updated` | S→C | `{node_id, config: {}}` | — |
| `node.rename` | C→S | `{node_id, name}` | `node.renamed` |
| `node.renamed` | S→C | `{node_id, name}` | — |

**注意：**
- `node.create` 的 `position` 由前端提供（用户点击位置），后端生成 `node_id` 并持久化。
- `node.move` **仅在 dragend 时发送一次**。拖拽过程中前端乐观更新本地 UI（无网络请求），用户松手后发送最终位置。后端收到后持久化并广播 `node.moved`。
- `node.update_config` 的 `config` 合并到已有配置（partial update），不是全量替换。
- **配置保存 debounce 策略：**
  - **即时控件**（switch/toggle/select/checkbox）：值变更时立即发送 `node.update_config`
  - **文本输入**（input/textarea，如 skill_prompt、端点 URL）：前端 500ms debounce 后发送
  - **设为默认**（`config.save_default`）：用户点击按钮时显式发送，不 debounce
  - 前端需在 debounce 期间显示待保存状态（如输入框边框变黄色），保存成功后恢复

---

### 4.4 连线 CRUD

| action | dir | params | 响应事件 |
|---|---|---|---|
| `connection.create` | C→S | `{from_node, from_port, to_node, to_port, type}` | `connection.created` |
| `connection.created` | S→C | `{connection: ConnectionDef}` | — |
| `connection.delete` | C→S | `{connection_id}` | `connection.deleted` |
| `connection.deleted` | S→C | `{connection_id}` | — |

**后端校验：**
- `from_port` 必须存在于 `from_node` 的输出端口定义中。
- `to_port` 必须存在于 `to_node` 的输入端口定义中。
- 端口 `data_type` 必须兼容。
- 不允许闭环（DAG 检查）。

---

### 4.5 执行控制

| action | dir | params | 响应事件 |
|---|---|---|---|
| `pipeline.run` | C→S | `{}` | `pipeline.started` → 逐节点 `node.status_changed` → `pipeline.completed` |
| `pipeline.started` | S→C | `{execution_id}` | — |
| `pipeline.completed` | S→C | `{execution_id}` | — |
| `pipeline.stop` | C→S | `{}` | `pipeline.stopped` |
| `pipeline.stopped` | S→C | `{execution_id}` | — |
| `node.trigger` | C→S | `{node_id}` | 手动触发某节点（跳过上游依赖） |
| `node.status_changed` | S→C | `{node_id, status, summary?, progress?, data?}` | — |

**`node.status_changed` params：**
```json
{
  "node_id": "stt_listen_01",
  "status": "processing",
  "summary": "识别: A点有敌人...",
  "progress": 0.45,
  "data": { "text": "A点有敌人", "trigger_keyword": null },
  "condition_result": null
}
```

**状态枚举：** `"pending"` | `"processing"` | `"completed"` | `"error"` | `"listening"`

**`condition_result` 字段**（仅 listener + 条件判断节点携带）：

| condition_result | 含义 | 下游行为 |
|---|---|---|
| `null` / 不携带 | 非条件节点，正常流转 | 按 trigger 规则执行下游 |
| `"matched"` | 条件满足（如关键词命中） | 触发下游节点链 |
| `"skipped"` | 条件不满足 | 不触发下游，listener 回到 `listening` 等待下一轮 |

**listener 节点生命周期（支持循环回路）：**

```
listening → (音频到达) → processing → completed {condition_result: "matched"}
                                                    ↓
                                          触发下游链 → ... → ⑨ 播放完成
                                                    ↓
                                          listener 自动回到 listening ←── 循环
                                          
listening → (音频到达) → processing → completed {condition_result: "skipped"}
                                                    ↓
                                          listener 自动回到 listening（不触发下游）
```

> **解释：** 原型中的"⑤ 不含关键词→回环到④继续监听"就是 `condition_result: "skipped"`。"含关键词→触发⑥"就是 `condition_result: "matched"`。`listening` 状态替代了原来只用 `pending` 表达"等待中"的模糊语义——`pending` 是尚未开始，`listening` 是已经启动并在循环等待。

#### 4.5.1 节点实时日志

后端在执行过程中向每个节点推送实时日志行，节点日志 tab 持续追加显示。

| action | dir | params | 说明 |
|---|---|---|---|
| `node.log_entry` | S→C | `{node_id, timestamp, level, message, highlight?}` | 推送一条日志到指定节点 |

**`node.log_entry` params：**
```json
{
  "node_id": "stt_listen_01",
  "timestamp": "14:23:05",
  "level": "info",
  "message": "识别: \"A点有敌人，注意\"",
  "highlight": false
}
```

**日志级别 `level`：**

| level | 前端渲染颜色 | 语义 |
|---|---|---|
| `muted` | `outline-variant` (#8b90a0) | 普通调试信息（如"接收到音频帧 #4521"） |
| `info` | `primary` (#adc7ff) | 重要业务信息（如"识别: A点有敌人"） |
| `success` | `secondary` (#4edea3) | 成功操作（如"OCR引擎加载完成"，"播放完成"） |
| `warn` | `tertiary-container` (#ef6719) | 触发/条件匹配（如"关键词匹配→触发！"） |
| `error` | `error` (#ffb4ab) | 错误信息 |

**`highlight` 字段：**
- `false`（默认）：正常渲染
- `true`：该行以 `animate-pulse` 闪烁 2 次后恢复，用于标记特殊事件（如关键词触发、流水线启动）

**前端实现规范：**
- 每个节点实例维护独立日志缓冲区，上限 **200 条**，超过则 FIFO 移除最旧条目
- 日志 tab 默认展示最新 **50 条**，向上滚动可加载更早记录
- 格式：`[timestamp] message`，颜色由 `level` 决定
- 节点创建时日志为空；节点删除时日志随之销毁
- `flow.load` 时**不恢复**历史日志（日志仅存在于当前会话）

---

### 4.6 撤销 / 重做

| action | dir | params | 说明 |
|---|---|---|---|
| `undo` | C→S | `{}` | 撤销当前 flow 上一步操作 |
| `redo` | C→S | `{}` | 重做 |
| `history.state` | S→C | `{can_undo, can_redo, last_action?}` | 每次操作后推送 |

**`history.state` params：**
```json
{
  "can_undo": true,
  "can_redo": false,
  "last_action": "node.move"
}
```

**可撤销的操作：** `node.create`, `node.delete`, `node.move`, `node.update_config`, `connection.create`, `connection.delete`

**不可撤销：** `pipeline.run`, `pipeline.stop`, `node.trigger`, `file.*`, `config.*`

**实现：** 后端为每个 flow 维护操作栈（上限 100 条），undo = 反向应用，redo = 重新应用。操作栈不跨 flow。

---

### 4.7 配置持久化

| action | dir | params | 响应事件 |
|---|---|---|---|
| `config.get_default` | C→S | `{scope: "node"\|"flow", target_id?}` | `config.default` |
| `config.default` | S→C | `{scope, target_id?, config: {}}` | — |
| `config.save_default` | C→S | `{scope, target_id?, config: {}}` | `config.saved` |
| `config.saved` | S→C | `{scope, target_id?}` | — |

**scope 说明：**
- `"node"` + `target_id` → 某类节点的默认配置（如 STT 节点默认用 SenseVoice）
- `"flow"` → 当前流程的全局配置（如 skill_prompt、画布尺寸）

---

### 4.8 侧栏管理

| action | dir | params | 说明 |
|---|---|---|---|
| `sidebar.tree` | S→C | `{groups: SidebarGroup[]}` | 连接时自动下发 |

**侧栏数据变更：** 侧栏数据来自 flows 和 groups，当流程增删或分组变更时，后端主动推送 `sidebar.tree`。

---

### 4.9 文件上传

| action | dir | params | 说明 |
|---|---|---|---|
| `file.upload_start` | C→S | `{name, size, mime_type, node_id?}` | 发起上传请求 |
| `file.upload_ready` | S→C | `{upload_id}` | 后端已准备接收 |
| `file.chunk` | C→S | Binary frame | 文件数据块 |
| `file.upload_progress` | S→C | `{upload_id, received, total}` | 可选进度推送 |
| `file.upload_done` | S→C | `{upload_id, file_id, name, size, mime_type}` | 上传完成 |
| `file.upload_error` | S→C | `{upload_id, error}` | 上传失败 |
| `file.upload_cancel` | C→S | `{upload_id}` | 取消上传 |

**上传流程：**

```
Client                              Server
  |                                     |
  |-- file.upload_start (JSON) -------->|  ① 告知文件名/大小/MIME/node_id
  |<-- file.upload_ready (JSON) --------|  ② 分配 upload_id，准备接收
  |                                     |
  |== BINARY frame (chunk 1) ==========>|  ③ 数据块（含 msg_id 头）
  |<-- file.upload_progress (可选) -----|  ④ 进度更新
  |== BINARY frame (chunk N) ==========>|  ⑤ 最后一块
  |                                     |
  |<-- file.upload_done (JSON) ---------|  ⑥ 返回 file_id
  |                                     |
```

**Binary frame 结构：**
```
Byte 0-3:   header_length (uint32, big-endian) — msg_id 的 UTF-8 字节数
Byte 4-N:   msg_id (UTF-8 string) — 关联 file.upload_start 的 msg_id
Byte N+1-*: file_data — 原始文件二进制数据
```

**大小限制：** 默认 100MB（后端 `settings.max_upload_size` 配置）。

**分块建议：** 前端按 256KB 分块发送 binary frame（避免单帧过大阻塞）。

---

### 4.10 通知中心（顶部铃铛）

原型顶部导航栏右侧有铃铛图标按钮。后端通过以下事件驱动通知系统。

| action | dir | params | 说明 |
|---|---|---|---|
| `important_update` | S→C | `{title, content, level, node_id?}` | 实时推送一条通知 |
| `notification.list` | C→S | `{limit?, before?}` | 查询历史通知 |
| `notification.list_result` | S→C | `{items: NotificationItem[], unread: int}` | 返回通知列表 + 未读计数 |
| `notification.mark_read` | C→S | `{notification_id?}` | 标记已读（缺省 = 全部已读） |

**`important_update` params：**
```json
{
  "title": "关键词触发",
  "content": "STT 检测到关键词 \"集合\"，已触发上下文构建",
  "level": "warning",
  "node_id": "stt_listen_01"
}
```

**level：** `"info"` | `"warning"` | `"error"` | `"success"`

**前端渲染：**
- 铃铛图标附带未读红点计数（badge），来自 `notification.list_result.unread`
- 点击铃铛弹出下拉列表，最多显示 20 条
- 列表底部的 "查看全部" 按钮或 "全部标为已读"
- `notification.list` 支持分页（`before` = 上一页最后一条的 id，向前翻页）
- 新通知到达时若下拉未打开，铃铛图标脉冲动画 + 红点数 +1

**后端存储：**
- 每条 `important_update` 自动写入通知历史（JSONL，按 flow_id 分文件）
- 后端自动清理 7 天前的通知
- 未读计数按 flow_id + 连接维护于内存，重连后通过 `notification.list` 恢复

---

### 4.11 通用 ACK / ERROR

| action | dir | params | 说明 |
|---|---|---|---|
| `ack` | S→C | `{ref_msg_id, ok: true}` | 操作成功确认 |
| `error` | S→C | `{ref_msg_id?, code, message, detail?}` | 操作失败 |

**错误码：**

| code | 含义 |
|---|---|
| `INVALID_PARAMS` | 参数校验失败 |
| `NODE_NOT_FOUND` | 节点不存在 |
| `CONNECTION_INVALID` | 连线规则校验失败 |
| `FLOW_NOT_FOUND` | 流程不存在 |
| `UPLOAD_TOO_LARGE` | 文件超限 |
| `UNSUPPORTED_TYPE` | 不支持的节点类型 |
| `PIPELINE_RUNNING` | 流程正在执行中，禁止编辑 |
| `INTERNAL_ERROR` | 服务端内部错误 |

---

## 5. 数据模型

### 5.1 FlowDef（流程完整定义）

```json
{
  "id": "darkzone_championship",
  "name": "暗区锦标赛",
  "group": "game_features",
  "icon": "sports_esports",
  "skill_prompt": "你是 TeamSpeak 频道监控助手。根据 OCR 信息和语音上下文，生成战术指导。",
  "canvas": { "width": 1700, "height": 1250 },
  "nodes": [ /* NodeDef[] */ ],
  "connections": [ /* ConnectionDef[] */ ]
}
```

### 5.2 NodeDef（节点定义）

```json
{
  "id": "ocr_01",
  "type": "ocr",
  "name": "OCR 识别",
  "position": { "x": 40, "y": 300 },
  "config": {
    "engine": "easyocr",
    "language": ["zh"],
    "confidence_threshold": 0.3
  },
  "input_mappings": [
    { "from_node": "image_input", "as_field": "image", "source_field": "image_data", "required": true }
  ],
  "trigger": {
    "type": "on_complete",
    "source_node": "image_input"
  },
  "listener": false
}
```

### 5.3 ConnectionDef（连线定义）

```json
{
  "id": "conn_img_to_ocr",
  "from_node": "image_input",
  "from_port": "img-out",
  "to_node": "ocr_01",
  "to_port": "ocr-in",
  "type": "data"
}
```

**type 枚举：** `"data"` | `"event"` | `"trigger"`

### 5.4 SidebarGroup（侧栏分组）

```json
{
  "id": "game_features",
  "name": "游戏",
  "icon": "folder",
  "children": [
    {
      "id": "dark_zone_group",
      "name": "暗区",
      "icon": "folder",
      "children": [
        {
          "id": "flow:darkzone_championship",
          "name": "游戏锦标赛",
          "icon": "sports_esports",
          "flow_id": "darkzone_championship",
          "type": "flow_ref"
        }
      ],
      "type": "group"
    }
  ],
  "type": "group"
}
```

### 5.5 ConfigDef（默认配置）

```json
{
  "scope": "node",
  "target_id": "stt_listen",
  "config": {
    "engine": "sensevoice",
    "keywords": ["求助", "集合", "撤退"],
    "sample_rate": 16000
  }
}
```

---

## 6. 连接管理

### 6.1 连接建立

1. 前端连接 `/ws`
2. 后端接受连接，立即发送：
   - `{type: "event", action: "node_types", params: {types: [...]}}`
   - `{type: "event", action: "sidebar.tree", params: {groups: [...]}}`
3. 前端渲染侧栏 + 节点类型面板
4. 前端按需发送 `flow.load` 加载特定流程

### 6.2 心跳

- 前端每 30 秒发送 WebSocket Ping frame
- 后端回复 Pong
- 若 90 秒未收到任何帧，任一端可关闭连接

### 6.3 断线重连

- 前端 `PipelineSocket` 自动重连，间隔 3 秒，指数退避上限 30 秒
- 重连成功后：
  1. 后端重新下发 `node_types` + `sidebar.tree`
  2. 前端对比 `activeFlowId`，若仍在则发送 `flow.load` 恢复状态
  3. 若之前有正在执行的 pipeline，后端推送 `pipeline.started` + 当前各节点 `node.status_changed` 恢复执行状态

### 6.4 并发编辑

- 单一 `/ws` 支持多 tab 连接同一 flow
- 后端在每次持久化操作后，向**所有订阅该 flow 的连接**广播 `event`
- 前端收到 event 后更新 UI（无需自身发 command 的连接也会收到）

---

## 7. 前端实现指南

### 7.1 消息发送

```js
// src/api/pipeline.js
class PipelineSocket {
  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws');
    // ...
  }

  sendCommand(flowId, action, params = {}) {
    const msg = {
      msg_id: crypto.randomUUID(),
      flow_id: flowId,
      type: 'command',
      action,
      params,
      ts: Date.now(),
    };
    this.ws.send(JSON.stringify(msg));
  }

  sendBinaryChunk(msgId, chunk) {
    const encoder = new TextEncoder();
    const idBytes = encoder.encode(msgId);
    const header = new ArrayBuffer(4);
    new DataView(header).setUint32(0, idBytes.length, false);
    // 合并 header + idBytes + chunk
    const combined = new Uint8Array(4 + idBytes.length + chunk.byteLength);
    combined.set(new Uint8Array(header), 0);
    combined.set(idBytes, 4);
    combined.set(new Uint8Array(chunk), 4 + idBytes.length);
    this.ws.send(combined);
  }
}
```

### 7.2 消息接收与分发

```js
onMessage(event) {
  if (event.data instanceof ArrayBuffer) {
    // binary frame — 忽略（文件上传是 client→server 单向）
    return;
  }

  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'event':
      this.emit(msg.action, msg.params);  // 分发到 stores
      break;
    case 'ack':
      // ack.ref_msg_id 匹配请求，可用于 loading 状态解除
      break;
    case 'error':
      // 显示错误通知
      break;
  }

  // 同时广播原始消息供调试
  this.emit('message', msg);
}
```

### 7.3 文件上传

```js
async uploadFile(flowId, file, nodeId = null) {
  const msgId = crypto.randomUUID();

  // ① 发起上传请求
  this.sendCommand(flowId, 'file.upload_start', {
    name: file.name,
    size: file.size,
    mime_type: file.type,
    node_id: nodeId,
  });

  // ② 等待 ready
  await this.waitForEvent('file.upload_ready', { upload_id: /.*/ });

  // ③ 分块发送
  const CHUNK_SIZE = 256 * 1024; // 256KB
  let offset = 0;

  // 使用 File.stream() 或 File.arrayBuffer() 分块读取
  const buffer = await file.arrayBuffer();
  while (offset < buffer.byteLength) {
    const chunk = buffer.slice(offset, offset + CHUNK_SIZE);
    this.sendBinaryChunk(msgId, chunk);
    offset += CHUNK_SIZE;
  }

  // ④ 等待完成
  const result = await this.waitForEvent('file.upload_done');
  return result.file_id;
}
```

---

## 8. 后端实现指南

### 8.1 消息路由

```python
# api/routes/ws_main.py
@router.websocket("/ws")
async def ws_main(websocket: WebSocket):
    await websocket.accept()

    # ① 下发元数据
    await send_event(websocket, "node_types", types=NodeRegistry.list_type_defs())
    await send_event(websocket, "sidebar.tree", groups=sidebar_service.get_tree())

    # ② 消息循环
    async for raw in websocket.iter_text():
        msg = json.loads(raw)
        if msg["type"] == "command":
            await handle_command(websocket, msg)
```

### 8.2 Command 分发

```python
COMMAND_HANDLERS = {
    "flow.load": handle_flow_load,
    "flow.list": handle_flow_list,
    "flow.create": handle_flow_create,
    "flow.delete": handle_flow_delete,
    "flow.rename": handle_flow_rename,
    "node.create": handle_node_create,
    "node.delete": handle_node_delete,
    "node.move": handle_node_move,
    "node.update_config": handle_node_update_config,
    "node.rename": handle_node_rename,
    "connection.create": handle_connection_create,
    "connection.delete": handle_connection_delete,
    "pipeline.run": handle_pipeline_run,
    "pipeline.stop": handle_pipeline_stop,
    "node.trigger": handle_node_trigger,
    "undo": handle_undo,
    "redo": handle_redo,
    "config.get_default": handle_config_get,
    "config.save_default": handle_config_save,
    "file.upload_start": handle_file_upload_start,
    "file.upload_cancel": handle_file_upload_cancel,
}

async def handle_command(ws, msg):
    handler = COMMAND_HANDLERS.get(msg["action"])
    if not handler:
        await send_error(ws, msg["msg_id"], "UNKNOWN_ACTION", f"Unknown action: {msg['action']}")
        return
    try:
        await handler(ws, msg)
    except ValidationError as e:
        await send_error(ws, msg["msg_id"], "INVALID_PARAMS", str(e))
    except Exception as e:
        await send_error(ws, msg["msg_id"], "INTERNAL_ERROR", str(e))
```

---

## 9. 实施对比

### 当前（混用，需要重构）

```
前端 ──REST──→ POST /api/files/upload
前端 ──REST──→ POST /api/ocr/recognize
前端 ──REST──→ POST /api/tts/*
前端 ──WS────→ ws://localhost:8000/ws/pipeline  ({type, data})
前端 ──WS────→ ws://localhost:8000/ws/teamspeak  (音频中继)
```

### 目标（统一）

```
前端 ──WS────→ ws://localhost:8000/ws  (流程编辑 + 执行 + 文件上传 + 配置 + 通知)

后端内部连接（不暴露给前端）：
后端 ──WS────→ ws://localhost:8080/teamspeak/voice  (Java Voice Bridge, 音频出入)
```

> `/ws/teamspeak` 从前端端点移除。音频数据通过后端内部的 AudioBus 流转，不经过前端。前端只通过 `/ws` 接收 `node.status_changed` 看音频状态，不需要接触原始音频帧。
