# TeamSpeak AI 前后端架构规范

> 定义前后端职责边界、数据模型、交互流程、以及从当前架构到目标架构的迁移路径。

---

## 1. 架构原则

### 1.1 核心模型：后端持有全部状态，前端是编辑器+渲染器

```
┌─────────────────────────────┐      ┌──────────────────────────────────┐
│         前端 (Vue 3)         │      │          后端 (FastAPI)            │
│                             │      │                                  │
│  ┌───────────────────────┐  │ WS   │  ┌────────────────────────────┐  │
│  │ 编辑器层              │  │◄────►│  │ Pipeline 数据管理层        │  │
│  │ · 拖拽节点位置        │  │      │  │ · 流程 CRUD               │  │
│  │ · 新建/删除节点       │  │      │  │ · 节点坐标存储            │  │
│  │ · 创建/删除连线       │  │      │  │ · 连线和端口校验          │  │
│  │ · 修改节点配置        │  │      │  │ · 操作历史 (undo/redo)    │  │
│  │ · 撤销/重做           │  │      │  │ · 默认配置持久化          │  │
│  └───────────────────────┘  │      │  │ · 文件存储                │  │
│                             │      │  └────────────────────────────┘  │
│  ┌───────────────────────┐  │      │                                  │
│  │ 渲染层                │  │      │  ┌────────────────────────────┐  │
│  │ · 画布渲染 (绝对定位) │  │      │  │ Pipeline 执行引擎          │  │
│  │ · SVG 连接线          │  │      │  │ · 节点调度                │  │
│  │ · 节点状态动画        │  │      │  │ · 实时状态推送            │  │
│  │ · 侧栏树形结构        │  │      │  │ · 上下文累积              │  │
│  │ · 详情面板            │  │      │  │ · 错误处理                │  │
│  └───────────────────────┘  │      │  └────────────────────────────┘  │
│                             │      │                                  │
│  ┌───────────────────────┐  │      │  ┌────────────────────────────┐  │
│  │ 连接管理层            │  │      │  │ 持久化层                  │  │
│  │ · WebSocket 生命周期  │  │      │  │ · Flow JSON 存储          │  │
│  │ · 断线重连            │  │      │  │ · 默认配置存储            │  │
│  │ · 文件上传分片        │  │      │  │ · 操作历史存储            │  │
│  └───────────────────────┘  │      │  │ · 文件磁盘存储            │  │
│                             │      │  └────────────────────────────┘  │
└─────────────────────────────┘      └──────────────────────────────────┘
```

### 1.2 三条铁律

1. **后端不猜前端布局** — 后端存储节点坐标但不计算布局。首次创建时前端给位置，之后用户拖拽调整。
2. **前端不存业务数据** — 所有数据（节点、连线、配置、文件引用）由后端持有，前端仅缓存渲染状态。浏览器刷新后通过 `flow.load` 恢复。
3. **一切走 WebSocket** — 不混用 REST，统一用 [websocket-protocol.md](./websocket-protocol.md) 中定义的消息格式。

---

## 2. 数据模型

### 2.1 存储单元

每个 Flow 在后端存储为一个 JSON 文件：

```
backend/
  data/
    flows/
      darkzone_championship.json    # Flow 完整定义
      another_flow.json
    defaults/
      node_stt_listen.json          # STT 节点默认配置
      node_ocr.json                 # OCR 节点默认配置
      ...
    history/
      darkzone_championship.jsonl   # 操作历史 (append-only)
      another_flow.jsonl
    uploads/
      {upload_id}/                  # 上传文件
        metadata.json
        file.bin
```

### 2.2 Flow JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "FlowDef",
  "type": "object",
  "required": ["id", "name", "nodes", "connections"],
  "properties": {
    "id":          { "type": "string" },
    "name":        { "type": "string" },
    "group":       { "type": "string" },
    "icon":        { "type": "string" },
    "skill_prompt": { "type": "string" },
    "canvas": {
      "type": "object",
      "properties": {
        "width":  { "type": "number", "default": 1700 },
        "height": { "type": "number", "default": 1250 }
      }
    },
    "nodes": {
      "type": "array",
      "items": { "$ref": "#/$defs/NodeDef" }
    },
    "connections": {
      "type": "array",
      "items": { "$ref": "#/$defs/ConnectionDef" }
    }
  },
  "$defs": {
    "NodeDef": {
      "type": "object",
      "required": ["id", "type", "position"],
      "properties": {
        "id":             { "type": "string" },
        "type":           { "type": "string" },
        "name":           { "type": "string" },
        "position":       { "type": "object", "properties": { "x": {"type":"number"}, "y": {"type":"number"} } },
        "config":         { "type": "object" },
        "input_mappings": { "type": "array", "items": {"$ref": "#/$defs/InputMapping"} },
        "trigger":        { "$ref": "#/$defs/TriggerConfig" },
        "listener":       { "type": "boolean", "default": false }
      }
    },
    "InputMapping": {
      "type": "object",
      "required": ["from_node", "as_field"],
      "properties": {
        "from_node":   { "type": "string" },
        "as_field":    { "type": "string" },
        "source_field": { "type": "string" },
        "required":    { "type": "boolean", "default": true }
      }
    },
    "TriggerConfig": {
      "type": "object",
      "required": ["type", "source_node"],
      "properties": {
        "type":        { "enum": ["on_complete", "on_keyword"] },
        "source_node": { "type": "string" },
        "keywords":    { "type": "array", "items": {"type":"string"} }
      }
    },
    "ConnectionDef": {
      "type": "object",
      "required": ["id", "from_node", "from_port", "to_node", "to_port"],
      "properties": {
        "id":        { "type": "string" },
        "from_node": { "type": "string" },
        "from_port": { "type": "string" },
        "to_node":   { "type": "string" },
        "to_port":   { "type": "string" },
        "type":      { "enum": ["data", "event", "trigger"], "default": "data" }
      }
    }
  }
}
```

### 2.3 节点类型定义（后端注册）

每个节点类型在后端 `NodeRegistry` 中注册，提供静态元数据。**这些元数据决定前端如何渲染节点（哪些 tab、端口在哪里）。**

```python
@dataclass
class TabDef:
    id: str                      # "config" | "detail" | "log" | "fulltext"
    label: str                   # "配置" | "详情" | "日志" | "全文"

@dataclass
class NodeTypeDef:
    type: str                    # e.g. "ocr"
    name: str                    # e.g. "OCR 识别"
    icon: str                    # Material Symbols name
    color: str                   # "primary" | "secondary" | "tertiary" | "outline"
    default_config: dict         # 创建时的默认配置
    tabs: list[TabDef]           # 节点内标签页列表（顺序即渲染顺序，可为空）
    ports: PortsDef              # 输入/输出端口定义

@dataclass
class PortsDef:
    inputs: list[PortDef]
    outputs: list[PortDef]

@dataclass
class PortDef:
    id: str                      # e.g. "image", "ocr_text"
    label: str                   # e.g. "图片 (PNG/JPG)"
    data_type: str               # "image" | "audio" | "string" | "string_array" | "messages" | "event"
    position: PortPosition       # 端口在节点卡片上的渲染位置

@dataclass
class PortPosition:
    side: str                    # "left" (输入) 或 "right" (输出)
    top: int                     # 距节点卡片顶部的像素偏移
```

**前端渲染规则：**
- `tabs` 按数组顺序渲染为节点内的 tab bar（`.tab-btn`）
- `tabs` 为空数组 `[]` 时，节点不显示 tab bar，直接显示 body 内容
- 输入端口渲染在节点左侧 `left: -7px`，`top` 由 `position.top` 指定
- 输出端口渲染在节点右侧 `right: -7px`，`top` 由 `position.top` 指定

**现有节点类型元数据：**

| type | tabs | 输入端口 | 输出端口 |
|---|---|---|---|
| `input_image` | `[]`（无 tab） | — | img-out(image, right, top:30), trigger-out(event, right, top:72) |
| `ocr` | config, detail, log | ocr-in(image, left, top:30) | ocr-out(string, right, top:55) |
| `stt_listen` | config, detail, log, fulltext | stt-in(audio, left, top:30) | stt-out(string, right, top:55) |
| `stt_history` | config, detail, log | hist-in(string, left, top:30) | hist-out(string_array, right, top:72), hist-trigger(event, right, top:110) |
| `context_build` | config, detail, log | ctx-in1~4 (left, 4个输入) | ctx-out(messages, right, top:55) |
| `llm` | config, detail, log | llm-in(messages, left, top:30) | llm-out(string, right, top:55) |
| `tts` | config, detail, log | tts-in(string, left, top:30) | tts-out(audio, right, top:55) |
| `ts_output` | `[]`（无 tab） | out-in(audio, left, top:30) | out-done(event, right, top:72) |

#### 2.3.1 detail tab 的前端渲染机制

**核心公式：`node.type` + `node.status` → Vue 组件**

前端维护一个类型→组件的注册表。后端只需要告诉前端"这是什么类型(type)、当前状态(status)、配置是什么(config)"，前端查找组件并渲染。

```js
// 前端组件注册表 (components/pipeline/nodes/registry.js)
export const nodeComponentRegistry = {
  input_image:   () => import('./InputImageNode.vue'),
  ocr:           () => import('./OcrNode.vue'),
  stt_listen:    () => import('./STTListenNode.vue'),
  stt_history:   () => import('./STTHistoryNode.vue'),
  context_build: () => import('./ContextBuildNode.vue'),
  llm:           () => import('./LLMNode.vue'),
  tts:           () => import('./TTSNode.vue'),
  ts_output:     () => import('./TSOutputNode.vue'),
}
```

**detail tab（或 body，当节点无 tab 时整张卡片）的渲染逻辑：**

```
接收 node.status_changed { node_id, status, ... }
  → 查找 node.type → 组件
  → 组件内部 switch(node.status):
      pending    → <等待/上传/文件选择组件>
      processing → <进度条/流式文本/动画组件>
      completed  → <结果展示/数据面板组件>
      error      → <ErrorDisplay 组件>
```

**具体映射：**

| node.status | input_image | stt_listen | llm | ocr |
|---|---|---|---|---|
| `pending` | AudioFileUploader（拖拽上传） | "等待音频流..."文本 | "等待上游上下文..."文本 | "等待图片..."文本 |
| `processing` | 上传进度条 + 百分比 | 实时识别文本 + 关键词点亮 + nodePulse | StreamingText（流式光标） | 识别中 spinner |
| `completed` | 文件名/大小/类型标签 | 触发关键词高亮 + 完成标记 | TextDisplay（完整回复，含 reasoning） | OCR 文本块 |
| `error` | "上传失败：xxx" | "STT 错误：xxx" | "LLM 调用异常：xxx" | "OCR 失败：xxx" |

> **后端不关心前端组件细节。** 后端只发 `type`、`status`、`config`、`data`。前端决定如何用 Vue 组件呈现这些数据。

---

## 3. 前后端职责边界

### 3.1 职责矩阵

| 能力 | 后端 | 前端 | 说明 |
|---|---|---|---|
| **数据持久化** | 全部 | 无 | 后端序列化 Flow JSON、操作历史、默认配置到磁盘 |
| **数据校验** | 全部 | 辅助 | 后端校验连线规则、端口类型匹配、DAG 无环；前端做格式合法性预览 |
| **节点坐标** | 存储 | 提供初始值 + 拖拽更新 | 用户拖拽后前端 `node.move` → 后端持久化并广播 |
| **连线规则** | 校验 | 拖拽时视觉反馈 | 后端拒绝无效连线并返回 error |
| **可用节点类型** | 注册 + 下发 | 渲染 palette | 连接时 `node_types` 下发，新建节点时展示 |
| **节点自动布局** | 可选执行 | 不执行 | 后端可提供 `flow.auto_layout` 命令触发自动排列 |
| **执行引擎** | 全部 | 仅展示 | 后端 PipelineEngine 调度节点；前端渲染 `node.status_changed` |
| **undo/redo** | 维护操作栈 | 发送命令 | 后端维护每个 flow 的操作历史（上限 100 条），前端 Ctrl+Z 触发 |
| **默认配置** | 存储 + 下发 | 编辑 + 提交 | 用户修改默认配置后通过 `config.save_default` 持久化 |
| **侧栏结构** | 构建 + 下发 | 渲染 | 从 flows 和 groups 自动生成树 |
| **文件存储** | 磁盘存储 | 分片发送 | 文件以 binary frame 发送，后端存盘并返回 file_id |
| **画布网格/背景** | 无 | 纯 CSS | 前端网格背景、缩放、平移 |

### 3.2 不需要后端参与的前端能力

- 画布缩放（zoom）、平移（pan）
- 节点 hover/pulse 动画
- SVG 连接线渲染（坐标从后端数据生成路径）
- 侧栏折叠/展开
- 详情面板切换
- 流程视图切换（全部 / 数据流 / 事件流）
- 滚动条样式
- 颜色主题
- 所有 CSS 动画

---

## 4. 生命周期

### 4.1 完整交互序列

```
[应用启动]
  前端连接 /ws
  ← 后端下发 node_types (可用节点类型列表)
  ← 后端下发 sidebar.tree (侧栏结构)
  ← 后端下发 connection.status (各服务连接状态)

[服务状态变更]
  ← 后端主动推送 connection.status (ts_bot 断连/重连, pipeline 状态切换)

[用户选择流程]
  前端发送 flow.load { flow_id: "darkzone_championship" }
  ← 后端下发 flow.loaded (完整 Flow JSON: nodes + connections + canvas)

[前端渲染画布]
  根据 nodes[].position 绝对定位节点
  根据 connections[] 绘制 SVG 连接线
  根据 flow.skill_prompt 设置 LLM 系统提示词

[用户编辑节点]
  拖拽节点       → 前端本地移动 UI（乐观渲染），dragend 时发送 node.move → node.moved
  新建节点       → node.create  → node.created
  删除节点       → node.delete  → node.deleted (自动删除相关连线)
  修改配置       → node.update_config → node.config_updated
    即时控件       → 值变更时立即发送
    文本输入       → 500ms debounce 后发送（debounce 期间输入框黄色边框）
    设为默认       → config.save_default 显式发送
  创建连线       → connection.create → connection.created 或 error
  删除连线       → connection.delete → connection.deleted

[用户撤销/重做]
  Ctrl+Z → undo → history.state (更新 can_undo/can_redo)
  Ctrl+Y → redo → history.state

[用户触发执行]
  上传文件       → file.upload_start → file.upload_ready → binary chunks → file.upload_done
  触发执行       → pipeline.run → pipeline.started
  ← 逐节点推送 node.status_changed (pending → processing → completed/error)
  ← listener 节点: listening → processing → completed {condition_result} → listening (循环)
  ← pipeline.completed

[条件路由（关键词匹配）]
  ⑤ History 完成 {condition_result: "matched"}   → 触发⑥ ContextBuild → ⑦ LLM → ⑧ TTS → ⑨ Output
  ⑤ History 完成 {condition_result: "skipped"}   → 不触发下游，回到④ STT 继续 listening

[应用关闭]
  前端断开连接
  后端清理该连接的所有 subscription
  (数据已实时持久化，无额外保存步骤)
```

### 4.2 并发编辑

```
[用户 A]                               [用户 B]
  │── node.move (x:100, y:200) ──→ 后端
  │                                    │
  │  ←── node.moved ──────────────── 后端 ──→ node.moved ←── │
  │  (A 的 UI 确认)                      │  (B 收到更新)
  │                                    │
  │                                    │── node.move ──→ 后端
  │  ←── node.moved ←── 后端 ←──────  │
  │  (A 收到 B 的更新)                  │
```

所有编辑操作广播到订阅同一 flow 的所有 WebSocket 连接。

### 4.3 编辑 vs 执行的互斥

- 流程 **正在执行中**（status=running）：后端拒绝编辑类 command（node.*, connection.*），返回 error `PIPELINE_RUNNING`。
- 流程 **空闲或已完成**：允许编辑。
- 前端在收到 `pipeline.started` 时进入只读模式，收到 `pipeline.completed` 时恢复编辑。

---

## 5. 节点实时日志

### 5.1 机制

后端在执行过程中通过 `node.log_entry` 事件向每个节点推送实时日志。前端在每个节点的日志 tab 中渲染。

**这不是**全局日志（footer important events），而是**节点级别**的诊断日志。

### 5.2 推送时机

| 场景 | level | 示例 |
|---|---|---|
| 节点开始处理 | `info` | `接收上下文 (tokens: 486)` |
| 处理中关键步骤 | `info` | `识别: "A点有敌人"` |
| 普通轮询/心跳 | `muted` | `接收到音频帧 #4521` |
| 操作成功 | `success` | `EasyOCR 引擎加载完成` |
| 触发条件匹配 | `warn` | `★ 关键词匹配: "集合" → 触发!` |
| 错误发生 | `error` | `STT 模型加载失败: model not found` |

### 5.3 前端渲染

```
┌─────────────────────────────────────┐
│ [配置] [输入/输出] [日志] [全文]    │ ← tabs
├─────────────────────────────────────┤
│ [14:23:05] 接收到音频帧 #4521       │ ← muted
│ [14:23:05] 识别: "A点有敌人，注意"   │ ← info
│ [14:23:06] 无关键词 → 继续监听       │ ← muted
│ [14:23:08] 接收到音频帧 #4522        │ ← muted
│ [14:23:08] 识别: "需要集合"          │ ← info
│ [14:23:08] ★ 关键词匹配 → 触发!     │ ← warn + highlight pulse
│ ...                                 │
│                        共 127 条 ───│ ← 底部计数
└─────────────────────────────────────┘
```

### 5.4 缓冲区规则

- **上限 200 条**，超过后移除最旧条目（FIFO）
- 默认展示最新 **50 条**，向上滚动加载更早记录
- 新日志到达时，若用户在日志 tab 且滚动在底部 → 自动滚动到底部
- 若用户已向上滚动查看历史 → 不自动滚动，显示 "↓ 新日志 (3)" 按钮
- **`flow.load` 不恢复历史日志**，日志仅在当前会话存活
- 节点删除时日志缓冲区随之销毁
- 节点类型不包含 `log` tab → 后端仍可推送日志，前端缓存在内存但无 UI 展示

---

## 6. 撤销/重做机制

### 6.1 后端操作栈

每个 flow 维护两个栈（限制 100 条）：

```
undo_stack: [op_N, ..., op_2, op_1]  ← 最近的操作在栈顶
redo_stack: []                        ← 每次新操作时清空
```

### 6.2 操作记录格式

```json
{
  "seq": 42,
  "action": "node.move",
  "timestamp": "2026-04-28T14:23:01.456Z",
  "forward": {
    "node_id": "ocr_01",
    "new_position": { "x": 250, "y": 400 }
  },
  "reverse": {
    "node_id": "ocr_01",
    "old_position": { "x": 40, "y": 300 }
  }
}
```

### 6.3 可撤销操作

| action | forward | reverse |
|---|---|---|
| `node.create` | 创建节点 + 参数 | 删除节点 |
| `node.delete` | 删除节点 | 恢复节点 + 所有配置和连线 |
| `node.move` | new_position | old_position |
| `node.update_config` | new_config (partial) | old_config (相同 key) |
| `connection.create` | 创建连线 | 删除连线 |
| `connection.delete` | 删除连线 | 恢复连线 |

### 6.4 合并策略

短时间内（500ms）对同一节点的连续 `node.update_config`（如快速切换多个开关）合并为一条操作：

```
toggle engine: easyocr ─┐
toggle lang: zh         ─┤ → 合并为一条 update_config
toggle lang: zh,en      ─┘   (forward=last config, reverse=first config)
```

拖拽移动（`node.move`）不需要合并——已改为 dragend 单次提交。

---

## 7. 文件上传

### 7.1 为什么不用 REST

| 维度 | REST multipart | WebSocket Binary |
|---|---|---|
| 认证 | 需要单独 token/cookie | 复用 WebSocket 连接认证 |
| 进度 | 需要额外 SSE/轮询 | 同一连接推送 `file.upload_progress` |
| 架构一致性 | 破坏"一切走 WS"原则 | 统一 |
| 大文件 | HTTP body 限制 | 流式分片，无大小限制 |
| 带宽 | base64 增 33% | 原始二进制，零膨胀 |

### 7.2 分块参数

- **分块大小：** 256 KB（`CHUNK_SIZE = 262144`）
- **最大文件：** 100 MB（后端 `settings.max_upload_size` 可配置）
- **并发上传：** 同一连接串行（避免 binary frame 交错）

### 7.3 上传流程详细时序

```
Client                                              Server
  |                                                    |
  | ① file.upload_start                               |
  |    { name: "screenshot.png",                      |
  |      size: 2456789,                               |
  |      mime_type: "image/png",                      |
  |      node_id: "image_input" }                     |
  |──────────────────────────────────────────────────>|
  |                                                    |
  |                     ② file.upload_ready            |
  |                        { upload_id: "upl_abc123" } |
  |<──────────────────────────────────────────────────|
  |                                                    |
  | ③ BINARY frame (chunk 1, 256KB)                  |
  |    [header_len:4][msg_id:N][data:262144]           |
  |══════════════════════════════════════════════════>|
  |                                                    |
  | ③ BINARY frame (chunk 2, 256KB)                  |
  |══════════════════════════════════════════════════>|
  |                                                    |
  |                     ④ file.upload_progress (可选)  |
  |                        { upload_id,               |
  |                          received: 524288,        |
  |                          total: 2456789 }          |
  |<──────────────────────────────────────────────────|
  |                                                    |
  |     ... (chunk 3 ~ 9, 每块 256KB) ...             |
  |                                                    |
  | ③ BINARY frame (chunk 10, ~100KB, 最后一块)      |
  |══════════════════════════════════════════════════>|
  |                                                    |
  |                     ⑤ file.upload_done             |
  |                        { upload_id,                |
  |                          file_id: "file_xyz789",   |
  |                          name: "screenshot.png",   |
  |                          size: 2456789 }           |
  |<──────────────────────────────────────────────────|
  |                                                    |
```

### 7.4 异常处理

- **传输中断：** 前端重连后重新 `file.upload_start`，后端支持断点续传（通过 `received` 字段告知已接收字节数）。
- **超时：** 后端在上次收到 chunk 后 60 秒无数据则清理 upload session。
- **取消：** 前端发送 `file.upload_cancel { upload_id }`。

---

## 8. 默认配置机制

### 8.1 配置层级

```
Flow 配置 (skill_prompt, canvas 大小等)
  └── Node 实例配置 (实例级参数，如 OCR 语言)
        └── Node 类型默认配置 (创建新节点时的初始值)
```

### 8.2 流程

1. 用户展开右侧面板 → 切换到"配置" tab → 显示当前节点的 `config`
2. 用户修改参数（如更换 OCR 引擎从 EasyOCR 到 PaddleOCR）
3. 前端发送 `node.update_config { node_id: "ocr_01", config: { engine: "paddleocr" } }`
4. 后端持久化到 Flow JSON 的对应节点
5. 后端广播 `node.config_updated` 到所有订阅者
6. 用户勾选"设为默认" → 前端额外发送 `config.save_default { scope: "node", target_id: "ocr", config: { engine: "paddleocr" } }`
7. 后端写入 `data/defaults/node_ocr.json`
8. 下次创建 OCR 节点时，默认配置即为 PaddleOCR

---

## 9. 侧栏数据生成

### 9.1 后端生成规则

```python
def build_sidebar_tree(flows: list[FlowDef]) -> list[SidebarGroup]:
    """
    1. 扫描所有 flow 的 group 字段
    2. 按 `/` 分割 group → 树形结构
       例如: "game_features/暗区" → 游戏 > 暗区 > [flows]
    3. 根节点固定: "工作流" (系统 flows), "系统设置" (静态)
    """
```

### 9.2 输出格式

```json
{
  "groups": [
    {
      "id": "workflows",
      "name": "工作流",
      "icon": "account_tree",
      "type": "section",
      "children": [
        {
          "id": "game_features",
          "name": "游戏",
          "icon": "folder",
          "type": "group",
          "children": [
            {
              "id": "dark_zone",
              "name": "暗区",
              "icon": "folder",
              "type": "group",
              "children": [
                {
                  "id": "flow:darkzone_championship",
                  "type": "flow_ref",
                  "flow_id": "darkzone_championship",
                  "name": "游戏锦标赛",
                  "icon": "sports_esports"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "id": "workflow_config",
      "name": "工作流配置",
      "icon": "tune",
      "type": "section",
      "children": [
        { "id": "action:new_flow", "type": "action", "name": "新建工作流", "icon": "add" },
        { "id": "action:flow_manage", "type": "action", "name": "流程管理", "icon": "account_tree" }
      ]
    },
    {
      "id": "system_settings",
      "name": "系统设置",
      "icon": "settings",
      "type": "section",
      "children": [
        { "id": "action:ocr_settings", "type": "action", "name": "OCR设置", "icon": "document_scanner" },
        { "id": "action:llm_settings", "type": "action", "name": "LLM设置", "icon": "psychology" },
        { "id": "action:stt_settings", "type": "action", "name": "STT设置", "icon": "mic" },
        { "id": "action:tts_settings", "type": "action", "name": "TTS设置", "icon": "record_voice_over" }
      ]
    }
  ]
}
```

### 9.3 "最近访问" 列表

前端维护，不依赖后端。使用 `localStorage` 存储最近 5 条访问的 flow_id，在侧栏底部渲染。

---

## 10. 前端架构调整

### 10.1 当前架构 vs 目标架构

| 模块 | 当前 | 目标 |
|---|---|---|
| `src/api/files.js` | Axios REST 文件操作 | **删除**，功能合并到 `pipeline.js` |
| `src/api/ocr.js` | fetch() OCR 调用 | **删除**，功能合并到 `pipeline.js` |
| `src/api/pipeline.js` | 简单的 `{type, data}` WS | 升级为信封格式 + binary frame 支持 |
| `src/utils/layout.js` | DAG 自动布局算法 | **删除**，坐标由后端提供 |
| `src/stores/pipeline.js` | 流程执行状态 | 拆分：编辑状态 + 执行状态 |
| `src/stores/sidebar.js` | 从 feature configs 构建 | 直接接收 `sidebar.tree` |

### 10.2 推荐 Store 拆分

```
src/stores/
  editor.js       ← 新增：流程编辑状态 (nodes, connections, undo/redo, dirty flag)
  execution.js    ← 重构自 pipeline.js：运行时状态 (node_status, streaming data)
  sidebar.js      ← 重构：接收 sidebar.tree 直接渲染
  files.js        ← 保留：文件上传进度和文件列表缓存
```

### 10.3 Editor Store 设计要点

```js
// stores/editor.js
export const useEditorStore = defineStore('editor', () => {
  // —— 状态 ——
  const flowId = ref(null)
  const flowMeta = ref({})           // name, group, icon, skill_prompt, canvas
  const nodes = ref([])              // NodeDef[]
  const connections = ref([])        // ConnectionDef[]
  const canUndo = ref(false)
  const canRedo = ref(false)

  // —— 加载 ——
  async function loadFlow(id) {
    const flow = await socket.sendCommand(id, 'flow.load') // 返回 Promise<FlowDef>
    flowId.value = id
    flowMeta.value = { ...flow, nodes: undefined, connections: undefined }
    nodes.value = flow.nodes
    connections.value = flow.connections
  }

  // —— 编辑操作 ——
  async function createNode(type, position) { /* node.create */ }
  async function deleteNode(nodeId) { /* node.delete */ }
  // 拖拽：过程中乐观更新本地 UI，dragend 时发送最终位置
  async function moveNode(nodeId, x, y) { /* node.move — 仅在 dragend 调用 */ }
  // 配置：即时控件立即发送，文本输入 500ms debounce
  async function updateNodeConfig(nodeId, config) { /* node.update_config */ }
  const debouncedUpdateConfig = debounce(updateNodeConfig, 500)
  async function createConnection(fromNode, fromPort, toNode, toPort) { /* connection.create */ }
  async function deleteConnection(connId) { /* connection.delete */ }
  async function undo() { /* undo */ }
  async function redo() { /* redo */ }

  // —— WebSocket 事件处理 ——
  function onNodeCreated({ node }) { nodes.value.push(node) }
  function onNodeDeleted({ node_id }) { nodes.value = nodes.value.filter(n => n.id !== node_id) }
  function onNodeMoved({ node_id, position }) { /* update node position */ }
  // ... 等等

  return { flowId, flowMeta, nodes, connections, canUndo, canRedo, /* ... */ }
})
```

---

## 11. 后端架构调整

### 11.1 新增模块

```
backend/
  data/                          ← 新增：数据目录
    flows/                       ← 流程 JSON 持久化
    defaults/                    ← 默认配置 JSON 持久化
    history/                     ← 操作历史 JSONL
    uploads/                     ← 上传文件
  core/
    flow/
      manager.py                 ← 新增：流程数据管理 (CRUD, 文件持久化, 侧栏构建)
    history/
      manager.py                 ← 新增：操作历史管理 (undo/redo 栈)
    config/
      defaults.py                ← 新增：默认配置管理
    upload/
      chunk_receiver.py          ← 新增：分块文件接收
  api/
    routes/
      ws_main.py                 ← 新增：主 WebSocket 端点 (合并 ws_pipeline + 编辑功能)
      ws_teamspeak.py            ← 重构：改为后端内部音频桥接模块（连接 Java Voice Bridge），不再暴露前端端点
```

### 11.2 废弃模块

| 文件 | 处理方式 |
|---|---|
| `api/routes/files.py` | 删除 REST 文件路由，合并到 `ws_main.py` |
| `api/routes/ocr.py` | 删除 REST OCR 路由 |
| `api/routes/ws_pipeline.py` | 合并到 `ws_main.py` |

### 11.3 更新模块

| 文件 | 变更 |
|---|---|
| `main.py` | 移除 files/ocr 路由注册；注册新的 `/ws` 端点 |
| `core/pipeline/definition.py` | 扩展 `NodeTypeDef` 增加端口定义 |
| `core/pipeline/registry.py` | 补充 `list_type_defs()` 方法 |
| `core/pipeline/engine.py` | 保持执行逻辑不变；增加并发编辑互斥 |

### 11.4 Flow Manager 设计要点

```python
# core/flow/manager.py
class FlowManager:
    """管理流程数据的 CRUD 和持久化"""

    def __init__(self, data_dir: str):
        self.flows_dir = Path(data_dir) / "flows"
        self.flows_dir.mkdir(parents=True, exist_ok=True)

    def list_flows(self) -> list[FlowSummary]:
        """扫描 flows/ 目录，返回所有流程摘要"""
        ...

    def load_flow(self, flow_id: str) -> FlowDef:
        """从 JSON 文件加载完整流程定义"""
        ...

    def save_flow(self, flow: FlowDef):
        """序列化并保存到磁盘"""
        ...

    def delete_flow(self, flow_id: str):
        """删除流程及其操作历史"""
        ...

    def create_flow(self, name: str, group: str, icon: str) -> FlowDef:
        """创建新流程，生成唯一 ID"""
        ...

    def build_sidebar_tree(self) -> list[SidebarGroup]:
        """从所有流程生成侧栏树结构"""
        ...
```

---

## 12. 迁移路径

### 12.1 阶段 1

1. 创建 `api/routes/ws_main.py`，实现新的 `/ws` 端点（与现有 `/ws/pipeline` 并行运行）。
2. 实现信封格式解析和 `action` 路由。
3. 先实现 `flow.list` / `flow.load` / `sidebar.tree` / `node_types` 只读命令。

### 12.2 阶段 2

1. 实现 `node.create/delete/move/update_config` + `connection.create/delete`。
2. 实现后端操作历史（undo/redo）。
3. 前端 `editor.js` store 对接。

### 12.3 阶段 3

1. 实现 binary frame 解析。
2. 实现断点续传。
3. 删除 `files.py` 和 `ocr.py` REST 路由。

### 12.4 阶段 4

1. 前端删除 `layout.js`、`files.js`、`ocr.js`。
2. 前端切换到新的 `editor.js` + 重构的 `pipeline.js`。
3. 后端移除 `ws_pipeline.py`、`files.py`、`ocr.py`。
4. `/ws` 端点成为唯一流程入口。

---

## 13. 安全考量

### 13.1 输入校验

- 所有 `params` 必须经过 Pydantic 模型校验。
- 字符串字段限制最大长度（name ≤ 100, skill_prompt ≤ 10000）。
- 坐标值限制在画布范围内（0 ≤ x ≤ 5000, 0 ≤ y ≤ 5000）。

### 13.2 文件上传

- 后端校验 MIME type 白名单（`image/png`, `image/jpeg`, `image/webp`）。
- 后端通过 magic bytes 二次校验文件类型（防止 MIME 伪造）。
- 限制并发上传数量（每连接最多 1 个）。
- 文件存入非 Web 可访问目录，通过 `file_id` 间接访问。

### 13.3 WebSocket

- 单 IP 最多 5 个并发连接。
- 消息大小限制：text frame ≤ 1MB, binary frame ≤ 512KB。
- 30 秒无活动心跳检测。

---

## 14. 文档索引

| 文档 | 内容 |
|---|---|
| [ui-style-guide.md](./ui-style-guide.md) | UI 样式规范（颜色/字体/间距/组件/动画/毛玻璃） |
| [websocket-protocol.md](./websocket-protocol.md) | WebSocket 协议（信封格式/所有 action 定义/数据模型） |
| 本文档 | 架构规范（职责边界/生命周期/undo-redo/文件上传/迁移路径） |
