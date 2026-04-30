# 工作流编辑器 — 完整实施计划

> 基于现有前后端代码、[pipeline-editor-spec.md](./pipeline-editor-spec.md) 交互规格、[architecture-spec.md](./architecture-spec.md) 架构规范，定义工作流编辑器的具体实施步骤。

---

## 1. 现状分析

### 1.1 已实现的前端能力

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| WebSocket 客户端 | `src/api/pipeline.js` (268行) | ✅ 完成 | 信封协议、ack Promise、binary 上传、自动重连 |
| Editor Store | `src/stores/editor.js` (249行) | ✅ 完成 | nodes/connections CRUD、nodeTypes 缓存、undo/redo 触发、debounce |
| Execution Store | `src/stores/execution.js` (97行) | ✅ 完成 | 节点状态、日志缓冲区 (FIFO 200)、pipeline 生命周期 |
| PipelineView | `src/components/pipeline/PipelineView.vue` (372行) | ✅ 完成 | 画布、缩放、平移、网格、SVG 连线渲染、flow view 切换 |
| NodeCard | `src/components/pipeline/NodeCard.vue` (419行) | ✅ 完成 | 拖拽移动、端口渲染、tab bar、状态边框、进度条、徽章 |
| IOPort | `src/components/pipeline/IOPort.vue` (104行) | ✅ 完成 | 三种状态 (disconnected/connected/flowing)、hover 标签 |
| CanvasControls | `src/components/pipeline/CanvasControls.vue` (167行) | ✅ 完成 | 视图切换、缩放按钮、百分比输入 |
| DynamicPanel | `src/components/panels/DynamicPanel.vue` (273行) | ✅ 完成 | 详情/配置/日志/全文 tab |
| AppLayout | `src/components/layout/AppLayout.vue` (336行) | ✅ 完成 | 侧栏树、画布区、面板区、状态栏 |
| 组件注册表 | `src/components/pipeline/nodes/registry.js` (27行) | ⚠️ 骨架 | 8 种节点类型映射为 null，未实现专属组件 |

### 1.2 已实现的后端能力

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| WebSocket 端点 | `api/routes/ws_main.py` (882行) | ✅ 完成 | 24 个 command handler、连接管理、广播 |
| FlowManager | `core/flow/manager.py` (492行) | ✅ 完成 | Flow/node/connection CRUD、侧栏树构建 |
| HistoryManager | `core/history/manager.py` (255行) | ✅ 完成 | 独立 undo/redo 栈、JSONL 持久化、合并策略 |
| NodeRegistry | `core/pipeline/registry.py` (182行) | ✅ 完成 | 8 种节点类型元数据 + 7 种运行时类 |
| PipelineEngine | `core/pipeline/engine.py` (565行) | ✅ 完成 | 执行调度、listener 循环、downstream 链式触发 |
| EventEmitter | `core/pipeline/emitter.py` (149行) | ✅ 完成 | 5 种事件推送 (status/log/pipeline/important) |
| ChunkReceiver | `core/upload/chunk_receiver.py` | ✅ 完成 | 分块接收、断点续传 |
| DefaultsManager | `core/config/defaults.py` | ✅ 完成 | 节点默认配置持久化 |

### 1.3 缺失的核心交互

| 功能 | 前端 | 后端 | pipeline-editor-spec 对应 |
|------|------|------|--------------------------|
| 预览/编辑双模式切换 | ❌ | ✅ (edit lock 已有) | §3 |
| 悬浮工具面板（拖节点到画布） | ❌ | N/A | §4 |
| 端口拖拽连线 | ❌ | ✅ (校验逻辑已有) | §6.6 |
| 端口点击配置面板 | ❌ | ❌ (需新增 input source 数据模型) | §6.7 |
| 端口拖动位置 | ❌ | ❌ (需支持 port.move) | §6.4 |
| 侧栏 `⋮` 菜单 | ❌ | ❌ (需创建 flow 管理 action) | §2 |
| 新建工作流对话框 | ❌ | ✅ (flow.create 已有) | §2.4 |
| 流程设置（画布尺寸） | ❌ | ✅ (canvas 字段已有) | §10 |
| 节点专属 Vue 组件 | ❌ (registry.js 全 null) | N/A | — |
| 端口默认位置自动分布 | ❌ | ❌ (port.top 需动态计算) | §6.2 |

---

## 2. 实施阶段

### 阶段 A：模式系统（预览/编辑切换）

**目标**：实现流程模式（默认只读）与编辑模式之间的切换。

**前端改动：**

| 文件 | 改动 |
|------|------|
| `stores/editor.js` | 新增 `editMode: ref(false)` 状态 |
| `AppLayout.vue` | 顶栏根据 editMode 渲染不同按钮组；侧栏 `⋮` 菜单响应 |
| `PipelineView.vue` | 接收 `editMode` prop，控制端口可见、拖拽启用 |
| `NodeCard.vue` | 接收 `editMode` prop，禁用拖拽和交互 |

**顶栏按钮逻辑：**

```
editMode = false (流程模式):  [流程设置]              ← primary-btn 突出
editMode = true  (编辑模式):  [流程模式] [保存] [撤销] [重做]  ← ghost-btn
```

**后端改动**：无需改动（edit lock 已通过 `PIPELINE_RUNNING` 错误实现）。

### 阶段 B：悬浮工具面板 + 拖节点到画布

**目标**：编辑模式下画布左侧出现节点类型面板，支持拖拽到画布创建节点。

**新增文件：**

```
src/components/pipeline/NodePalette.vue    (~180行)
```

**组件设计：**

```
Props:  visible (Boolean)
State:  从 editorStore.nodeTypes 读取节点类型列表
行为:   mousedown 创建 ghost → mousemove 跟随 → mouseup 计算画布坐标 → editorStore.createNode()
```

**Ghost 元素**：`position: fixed; z-index: 9999; pointer-events: none`，内容为 icon + 节点名称。

**拖拽坐标转换**（与 `PipelineView.vue` 配合）：

```javascript
// screen → canvas 坐标
const rect = canvasEl.getBoundingClientRect();
const x = (e.clientX - rect.left + canvasEl.scrollLeft) / zoom - 110;
const y = (e.clientY - rect.top + canvasEl.scrollTop) / zoom - 20;
editorStore.createNode(nodeType, { x, y });
```

**现有可复用**：`editorStore.createNode()` 已实现，发送 `node.create` 命令。

### 阶段 C：端口拖拽连线

**目标**：从输出端口拖线到输入端口，创建 data/event 连线。

**改动文件：**

| 文件 | 改动 |
|------|------|
| `IOPort.vue` | 新增 `@mousedown` emit，区分拖拽 vs 点击 (移动阈值 > 3px) |
| `PipelineView.vue` | 新增临时 SVG `<line>` 渲染；在 `window` 层监听 mousemove/mouseup；高亮兼容/不兼容目标端口 |
| `stores/editor.js` | 复用 `createConnection()` 已有方法 |

**连线拖拽流程：**

```
IOPort mousedown (output port)
  → PipelineView 创建 temp-line (z-index: 200)
  → mousemove: 更新 temp-line 终点 + 检测悬停 input port
  → 悬停 input port: 校验 data_type 兼容性 → 加 .drag-over.valid / .invalid
  → mouseup: 兼容 → createConnection(); 不兼容/空白 → 取消
```

**端口兼容性校验**（前端实现，与后端 `FlowManager.validate_connection` 保持一致）：

```javascript
const COMPATIBLE = {
  image: ['image'],
  audio: ['audio'],
  string: ['string', 'string_array'],
  string_array: ['string_array', 'messages'],
  messages: ['messages'],
  event: []  // event 仅用于 event 类型连线，不走数据校验
};
```

### 阶段 D：端口点击配置面板

**目标**：点击输入端口弹出数据来源配置面板；点击输出端口查看下游连线。

**新增文件：**

```
src/components/pipeline/PortConfigPanel.vue    (~200行)
```

**Props：** `nodeId`, `portId`, `portDef` (PortDef), `side` ('input'|'output'), `position` (屏幕坐标)

**输入端口面板内容：**

```
数据来源:  ◉ 连线获取  ○ 本节点参数  ○ 手动默认值

[连线获取模式]
  当前连线: stt_listen.stt-out → 此端口  [移除连线]

[本节点参数模式]
  参数路径: config.[▼ engine/keywords/...]
  预览值: (当前值)

[手动默认值模式]
  默认值: [textarea / input]
```

**输出端口面板内容：**

```
下游连线:
  → context_build.ctx-in2  [移除连线]
```

**后端改动需求：**

NodeDef 的输入端口需要新增 `source` 字段来存储数据来源：

```json
// NodeDef 中每个输入端口的配置
"input_sources": {
  "ocr-in": {
    "type": "connection"           // "connection" | "default" | "param"
    // type=default 时:
    "default_value": "你好世界"
    // type=param 时:
    "param_path": "config.default_text"
  }
}
```

或者把这个信息挂在 NodeDef 顶层：

```json
{
  "id": "ocr_01",
  "type": "ocr",
  "port_sources": {
    "ocr-in": { "type": "default", "value": "固定文本" }
  }
}
```

**WebSocket 协议新增：**

| action | dir | params |
|--------|-----|--------|
| `port.set_source` | C→S | `{node_id, port_id, source: {type, value?, param_path?}}` |
| `port.source_updated` | S→C | `{node_id, port_id, source}` |

### 阶段 E：端口拖动位置

**目标**：用户可沿节点侧边垂直拖动端口圆点。

**改动文件：**

| 文件 | 改动 |
|------|------|
| `IOPort.vue` | 新增垂直拖动逻辑（`mousedown` + `mousemove` 仅 Y 轴） |
| `stores/editor.js` | 新增 `movePort(nodeId, portId, newTop)` → 发送 WebSocket |
| `PipelineView.vue` | 端口拖动时重绘连线（实时跟随） |

**后端改动：**

- `FlowManager` 新增 `move_port()` 方法，更新 `NodeTypeDef.ports[].position.top`
- WebSocket 新增 `port.move` / `port.moved` action
- `HistoryManager` 记录 `port.move` 操作（可撤销）

**端口默认位置算法**（创建节点时自动计算）：

```javascript
function calculateDefaultPortTops(portCount, nodeHeight = 140) {
  const headerH = 40, padding = 12;
  const area = nodeHeight - headerH - padding;
  if (portCount <= 1) return [headerH + area / 2];
  return Array.from({length: portCount}, (_, i) =>
    Math.round(headerH + area * (i + 1) / (portCount + 1))
  );
}
```

### 阶段 F：侧栏 `⋮` 菜单系统

**目标**：侧栏每一层级显示 `⋮` 按钮，弹出分级菜单。

**改动文件：**

| 文件 | 改动 |
|------|------|
| `AppLayout.vue` | 侧栏树每个节点渲染 `⋮` 按钮 + 弹出菜单组件 |
| `stores/editor.js` | 新增 `renameFlow()`, `duplicateFlow()`, `exportFlow()`, `importFlow()`, `disableFlow()`, `moveFlowToGroup()` |

**新增组件：**

```
src/components/layout/SidebarContextMenu.vue    (~100行)
```

**菜单项因层级而异：**

| 层级 | 菜单项 |
|------|--------|
| 根「工作流」 | 新建、导出全部、导入 |
| 子分组 | 新建子分组、重命名、导出分组、导入到分组 |
| 叶子工作流 | 重命名、复制、导出、导入替换、移动到分组、禁用/启用、删除 |

**新建工作流对话框：**

在 `AppLayout.vue` 中新增模态框组件（~80行），替代当前 `prompt()` 调用：
- 名称（必填）
- 分组（`/` 解析为多层目录）
- 图标选择器（Material Symbols 网格）
- 创建后调用 `flow.create` → 自动切换到新 flow → 进入流程模式

**后端改动：**

| 新增 action | 说明 |
|------------|------|
| `flow.duplicate` | 复制工作流（完整深拷贝 nodes + connections） |
| `flow.export` | 返回完整 Flow JSON（下载） |
| `flow.import` | 从 JSON 创建/替换工作流 |
| `flow.disable` / `flow.enable` | 切换禁用状态 |
| `flow.move_group` | 修改 group 字段 |
| `group.rename` | 批量修改所有该 group 下的 flow.group |

### 阶段 G：流程设置（画布尺寸）

**目标**：修改画布宽高，实时更新。

**前端改动：**

在 `AppLayout.vue` 中新增画布设置模态框，内容仅为 width/height 两个 number input。

```javascript
// 更新画布
editorStore.flowMeta.canvas = { width: newW, height: newH };
// 持久化
pipelineSocket.sendCommand(flowId, 'flow.update', { canvas: { width, height } });
```

**后端改动：**

| 新增 action | 说明 |
|------------|------|
| `flow.update` | 更新 flow 元数据（canvas 尺寸、name 等） |

---

## 3. 前端文件改动汇总

### 3.1 新增文件

| 文件 | 预计行数 | 说明 |
|------|---------|------|
| `src/components/pipeline/NodePalette.vue` | ~180 | 悬浮工具面板，拖节点到画布 |
| `src/components/pipeline/PortConfigPanel.vue` | ~200 | 端口数据来源配置面板 |
| `src/components/layout/SidebarContextMenu.vue` | ~100 | 侧栏 `⋮` 分级菜单 |
| `src/components/layout/FlowCreateModal.vue` | ~120 | 新建工作流对话框 |
| `src/components/layout/CanvasSettingsModal.vue` | ~60 | 画布尺寸设置 |
| `src/components/pipeline/nodes/InputImageNode.vue` | ~80 | 上传图片节点 body |
| `src/components/pipeline/nodes/STTListenNode.vue` | ~120 | STT 监听节点 body |
| `src/components/pipeline/nodes/LLMNode.vue` | ~100 | LLM 节点 body |
| `src/components/pipeline/nodes/OCRNode.vue` | ~60 | OCR 节点 body |
| 其他 4 个节点专属组件 | ~240 | ContextBuild/TTS/TSOutput/STTHistory |

### 3.2 修改文件

| 文件 | 改动范围 | 说明 |
|------|---------|------|
| `AppLayout.vue` | +120行 | 双模式顶栏、`⋮` 菜单、模态框集成 |
| `PipelineView.vue` | +80行 | editMode prop、连线拖拽、端口拖动 |
| `NodeCard.vue` | +40行 | editMode prop、端口点击 emit |
| `IOPort.vue` | +60行 | 点击/拖拽区分、垂直拖动、data_type 属性 |
| `stores/editor.js` | +80行 | editMode、port source/move、flow 管理方法 |
| `stores/execution.js` | +5行 | 无大改动 |
| `nodes/registry.js` | +20行 | 替换 null 为实际组件导入 |

### 3.3 总预估

| 类别 | 数量 |
|------|------|
| 新增文件 | ~11 个 |
| 修改文件 | ~7 个 |
| 新增代码 | ~1500 行 |
| 修改代码 | ~400 行 |

---

## 4. 后端改动汇总

### 4.1 新增 WebSocket Actions

| action | handler | 说明 |
|--------|---------|------|
| `port.set_source` | `handle_port_set_source` | 设置输入端口数据来源 |
| `port.move` | `handle_port_move` | 更新端口 top 位置 |
| `flow.duplicate` | `handle_flow_duplicate` | 深拷贝工作流 |
| `flow.export` | `handle_flow_export` | 返回完整 JSON |
| `flow.import` | `handle_flow_import` | 从 JSON 创建/替换 |
| `flow.disable` | `handle_flow_disable` | 禁用/启用 |
| `flow.move_group` | `handle_flow_move_group` | 移动分组 |
| `flow.update` | `handle_flow_update` | 更新 canvas 等元数据 |
| `group.rename` | `handle_group_rename` | 重命名分组 |

### 4.2 数据模型扩展

**NodeDef 新增 `port_sources` 字段：**

```json
{
  "id": "ocr_01",
  "type": "ocr",
  "port_sources": {
    "ocr-in": {
      "type": "connection"
    }
  }
}
```

支持三种来源：`{type: "connection"}` / `{type: "default", value: "..."}` / `{type: "param", param_path: "config.xxx"}`

**PortDef.position.top 支持动态更新**：`port.move` action 修改 `PortDef.position.top` 并持久化。

### 4.3 HistoryManager 扩展

新增可撤销操作：

| action | forward | reverse |
|--------|---------|---------|
| `port.move` | new_top | old_top |
| `port.set_source` | new_source | old_source |

### 4.4 改动文件

| 文件 | 改动范围 | 说明 |
|------|---------|------|
| `api/routes/ws_main.py` | +150行 | 9 个新 handler |
| `core/flow/manager.py` | +80行 | port source、port move、flow 管理扩展 |
| `core/history/manager.py` | +15行 | port 操作合并策略 |
| `core/pipeline/definition.py` | +10行 | PortSource 数据类 |

---

## 5. 实施顺序

```
阶段 A  模式系统          ← 基础设施，所有后续阶段依赖
  ↓
阶段 B  工具面板+拖节点     ← 核心编辑交互
  ↓
阶段 C  端口拖拽连线        ← 核心编辑交互
  ↓
阶段 D  端口点击配置面板    ← 精细配置
  ↓
阶段 E  端口拖动位置        ← 端口灵活布局
  ↓
阶段 F  侧栏⋮菜单          ← 工作流管理
  ↓
阶段 G  流程设置            ← 画布尺寸
  ↓
收尾    节点专属组件        ← 优化各节点 body 渲染
```

阶段 A 完成后即可开始 B/C 并行开发（两者无依赖关系）。D/E 依赖 C 的连线系统。F/G 独立可并行。

---

## 6. 关键设计决策

### 6.1 模式状态管理位置

`editMode` 放在 `editor.js` store 中，因为：
- 编辑锁 (`isReadOnly`) 已在 editor store
- 所有编辑操作 (createNode, moveNode 等) 都经过 editor store
- 组件只需读 `editorStore.editMode` 即可判断是否可交互

### 6.2 连线拖拽的 SVG 层

临时拖拽线放在 `PipelineView.vue` 的 `<svg>` 最上层（新 `<line>` 元素），而非独立 overlay。原因：
- 与已有 connections-svg 共享坐标系统
- 无需额外的屏幕坐标→画布坐标转换

### 6.3 端口面板定位

`PortConfigPanel.vue` 使用 `position: fixed` + 动态 `left/top`（基于端口 DOM 元素 `getBoundingClientRect()`）。原因：
- 面板需要突破节点卡片的 `overflow` 限制
- 参考端口圆点的屏幕坐标定位

### 6.4 默认端口位置

创建节点时不传 `port.position.top`，由前端根据端口数量自动计算均匀分布。原因：
- 保持 UI 简洁：用户看到的是自动居中、均匀分布的端口
- 用户拖动端口后才写入自定义 top 值
- 后端存储的 top 值仅作为 override

### 6.5 节点专属组件

使用 Vue 异步组件 (`defineAsyncComponent`) + `registry.js` 做动态导入。原因：
- 每种节点 type 的 body 渲染逻辑不同
- 按需加载减少初始 bundle
- 与 `DynamicPanel.vue` 的 tab 系统配合使用

---

## 7. 文件对照：需求 → 实现

| pipeline-editor-spec.md 章节 | 前端文件 | 后端改动 |
|------------------------------|---------|---------|
| §2 侧栏工作流管理 | `AppLayout.vue`, `SidebarContextMenu.vue`, `FlowCreateModal.vue` | `flow.*` 9 个新 action |
| §3 流程/编辑双模式 | `stores/editor.js`, `AppLayout.vue`, `PipelineView.vue`, `NodeCard.vue` | 无 |
| §4 悬浮工具面板 | `NodePalette.vue` (新) | 无 |
| §5 节点卡片 | 参考现有 `NodeCard.vue` (419行)，不改结构 | 无 |
| §6.2 端口默认位置 | 前端计算，创建节点时不传 top | 无 |
| §6.4 端口手动拖动 | `IOPort.vue`, `stores/editor.js` | `port.move` action + History |
| §6.6 端口拖拽连线 | `IOPort.vue`, `PipelineView.vue` | 复用 `connection.create` |
| §6.7 端口点击配置面板 | `PortConfigPanel.vue` (新) | `port.set_source` action |
| §7 数据类型兼容 | `PipelineView.vue` 前端校验 | 已有 `FlowManager.validate_connection` |
| §8 连线渲染 | `PipelineView.vue` 已有，不改 | 无 |
| §9 右侧详情面板 | `DynamicPanel.vue` 已有，不改 | 无 |
| §10 流程设置 | `CanvasSettingsModal.vue` (新) | `flow.update` action |
| §12 视图切换 | `CanvasControls.vue` 已有，不改 | 无 |
| §13 键盘快捷键 | `AppLayout.vue` 全局监听 | 无 |
| §14 撤销/重做 | `stores/editor.js` 发送 undo/redo | 已有 HistoryManager |
| §15 保存机制 | `pipeline.js` WebSocket | 已有持久化 |
| §16 节点类型定义 | 后端 `registry.py` 已有，前端 `editor.js` 缓存 | 无 |

---

## 8. 现有代码复用清单

以下现有代码**不需要修改**，可直接复用：

| 文件 | 复用内容 |
|------|---------|
| `src/api/pipeline.js` | `sendCommand()`, `uploadFile()`, 自动重连, ack Promise |
| `src/stores/editor.js` | `createNode()`, `deleteNode()`, `moveNode()`, `updateConfig()`, `createConnection()`, `deleteConnection()`, `undo()`, `redo()`, `init()` |
| `src/stores/execution.js` | `getNodeStatus()`, `getNodeLogs()`, 所有事件 handler |
| `src/components/pipeline/PipelineView.vue` | 画布缩放/平移、SVG 连线渲染、flow-view 切换 |
| `src/components/pipeline/NodeCard.vue` | 节点拖拽、tab bar、状态渲染、端口渲染 |
| `src/components/pipeline/IOPort.vue` | 端口圆点渲染、状态 class |
| `src/components/pipeline/CanvasControls.vue` | 视图切换、缩放控制 |
| `src/components/panels/DynamicPanel.vue` | 详情/配置/日志/全文 tab 渲染 |
| `src/components/layout/BottomStatusBar.vue` | 服务状态指示 |
| `src/components/layout/NotificationBell.vue` | 通知铃铛 |
| `api/routes/ws_main.py` | 全部已有 command handler、广播系统、连接管理 |
| `core/flow/manager.py` | Flow/node/connection CRUD、侧栏树构建 |
| `core/pipeline/engine.py` | Pipeline 执行、listener 循环、EventEmitter |
| `core/history/manager.py` | undo/redo 栈、JSONL 持久化 |
