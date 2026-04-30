# 工作流编辑器 — 交互需求规格

> 定义「新建工作流 → 拖拽配置管线 → 连线 → 运行」的完整界面布局、交互流程和功能需求。
> 本规格与 [websocket-protocol.md](./websocket-protocol.md)、[architecture-spec.md](./architecture-spec.md)、[ui-style-guide.md](./ui-style-guide.md) 互补，共同构成前端实现的完整参考。

---

## 1. 整体布局

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ① Top Nav Bar (56px, fixed, z-50)                                        │
│ ┌────────┬────────────────────────────────────────────────────────────┐  │
│ │Logo    │ 工作流名称 [流程设置] / [流程模式] [保存] [撤销] [重做]  铃铛│  │
│ └────────┴────────────────────────────────────────────────────────────┘  │
├────────┬───────────────────────────────────────────────┬──────────────────┤
│②Sidebar│            ③ Canvas (可缩放/平移)             │④ Right Panel     │
│256px   │   1700 × 1250 (默认), 网格背景                │ 320px, z-30      │
│z-40    │                                               │ fixed            │
│        │  ┌─────────┐     ┌─────────┐                │ (仅编辑模式显示)  │
│ 工作流树 │  │ ① 上传  │────→│ ② OCR   │                │ ┌──────────────┐ │
│ 各层⋮  │  │ image   │     │         │                │ │Header:节点名   │ │
│        │  └─────────┘     └─────────┘                │ │[配置][详情][日志]│ │
│        │   节点卡片 (绝对定位, 毛玻璃)                │ │              │ │
│ 系统设置 │                                               │ │ 可编辑配置项  │ │
│        │  ┌──────────┐ (编辑模式时悬浮)                │ │ [取消][保存]  │ │
│        │  │工具面板   │                                │ └──────────────┘ │
│        │  │节点类型列表│                                │                  │
│        │  └──────────┘                                │                  │
│        │                                               │                  │
│        │  [全部|数据流|事件流] [-] 100% [+] 适应       │                  │
├────────┴───────────────────────────────────────────────┴──────────────────┤
│ ⑤ Bottom Status Bar (32px, fixed, z-50)                                   │
│ ● TeamSpeakBot: 运行中  ● Backend: 健康  ● Pipeline: 编辑中  API|文档|支持 │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.1 五区域尺寸

| 区域 | 宽度 | 高度 | 定位 | z-index |
|------|------|------|------|---------|
| ① Top Nav Bar | 100% | 56px | fixed top-0 | z-50 |
| ② Sidebar | 256px | calc(100vh - 88px) | fixed left-0 top-14 | z-40 |
| ③ Canvas | flex-1, ml-64 | calc(100vh - 88px) | relative, overflow-auto | z-0 |
| ④ Right Panel | 320px | calc(100vh - 88px) | fixed right-0 top-14 | z-30 |
| ⑤ Bottom Status Bar | 100% | 32px | fixed bottom-0 | z-50 |

### 1.2 画布规格

| 属性 | 值 |
|------|-----|
| 默认尺寸 | 1700 × 1250 px |
| 最小尺寸 | 800 × 600 px |
| 最大尺寸 | 5000 × 5000 px |
| 网格单元 | 32px |
| 网格颜色 | `#31353d` (surface-variant), opacity 0.15 |
| 背景色 | `#121417` |
| 缩放范围 | 25% ~ 300% |
| 缩放步进 | 10% (按钮) / 连续 (滚轮) |
| 变换原点 | `transform-origin: 0 0` |

### 1.3 Canvas 内容区域内部结构

```
#canvas-content (position: relative, z-10, padding: 32px)
  ├── <svg id="connections-svg"> (position: absolute, top:0, left:0, pointer-events: none)
  │     ├── <defs> (箭头标记: arrowEvent, arrowData, arrowDataFlow)
  │     ├── <g class="data-only"> (数据连线组)
  │     └── <g class="event-only"> (事件连线组)
  │
  ├── <div class="node-card"> × N (absolute 定位的节点卡片)
  │     ├── .io-port (.input-port / .output-port) 端口圆点
  │     ├── .workflow-badge (步骤号徽章 ①②③...)
  │     ├── header (icon + title + 状态标签)
  │     ├── .tab-bar (可选，有 tab 的节点)
  │     └── .node-body (默认状态区 或 tab-content)
  │
  └── (empty-hint 占位，无节点时显示)
```

---

## 2. 侧栏 — 工作流管理

### 2.1 侧栏分区

侧栏仅保留两个分区：

```
┌──────────────────────────────┐
│ 📂 工作流                  ⋮ │ ← 根分组：仅 [新建] [导出全部] [导入]
│   └ 📁 游戏               ⋮ │ ← 子分组：仅 [新建子分组] [重命名] [导出] [导入]
│       └ 📁 暗区           ⋮ │ ← 子分组
│           └ 🔵 暗区锦标赛  ⋮ │ ← 工作流项：完整菜单
│           └ ○ 暗区日常    ⋮ │
│   └ 📁 默认               ⋮ │
│       └ ○ 测试工作流      ⋮ │
│                              │
│ ⚙ 系统设置                   │ ← 静态链接（无 ⋮ 菜单）
│   └ OCR设置                  │
│   └ LLM设置                  │
│   └ STT设置                  │
│   └ TTS设置                  │
│                              │
│ ─── 最近访问 ───              │ ← 底部分割线
│   暗区锦标赛                  │    最近 5 条，前端 localStorage
│   OCR 设置                   │
└──────────────────────────────┘
```

### 2.2 层级 `⋮` 菜单规则

**每一层级**都显示竖排三点图标 `⋮`（`more_vert`），菜单项因层级而异：

| 层级 | 类型 | 可用操作 |
|------|------|---------|
| 根「工作流」 | 根分组 | **新建**、**导出全部**、**导入** |
| 子分组（游戏/暗区） | 子分组 | **新建子分组**、**重命名**、**导出该分组**、**导入到该分组** |
| 叶子工作流 | 工作流 | **重命名**、**复制**、**导出**、**导入替换**、**📦 移动到分组**、**禁用/启用**、**删除** |

**各层级菜单示意：**

```
┌ 根分组 ──────────────┐  ┌ 子分组 ───────────────┐  ┌ 工作流项 ───────────────┐
│ ➕ 新建工作流         │  │ ➕ 新建子分组           │  │ ✏ 重命名                 │
│ ─────────────────── │  │ ✏ 重命名               │  │ 📋 复制                   │
│ 📥 导出全部          │  │ ───────────────────── │  │ ─────────────────────── │
│ 📤 导入工作流        │  │ 📥 导出该分组           │  │ 📥 导出                   │
└─────────────────────┘  │ 📤 导入到该分组         │  │ 📤 导入替换               │
                          └───────────────────────┘  │ ─────────────────────── │
                                                      │ 📦 移动到分组...          │  ← 弹出分组选择器
                                                      │ ─────────────────────── │
                                                      │ 🚫 禁用                   │
                                                      │ ─────────────────────── │
                                                      │ 🗑 删除                   │  ← 红色，二次确认
                                                      └─────────────────────────┘
```

### 2.3 移动分组

工作流项菜单中的「📦 移动到分组」：

1. 点击后弹出分组选择器——列出所有现有分组（扁平列表，如 `游戏/暗区`、`默认`）
2. 也可输入新分组路径（用 `/` 创建新层级）
3. 选择/输入后确认 → 工作流的 `group` 字段更新 → 侧栏树重建
4. 本质是修改 flow 的 `group` 字段

### 2.4 新建工作流对话框

毛玻璃模态框，居中显示 480px 宽玻璃卡片：

```
┌──────────────────────────────────────────────────┐
│  ⊕ 新建工作流                                    │
│                                                  │
│  名称 *     [____________________________]       │  ← 必填，max 50 字符
│  分组        [____________________________]       │  ← 可选，用 / 自动解析为多层目录
│  图标                                            │
│  [🏆][🎮][🧠][🎤][📄][📷] [📁][🎯][🔊] ...  │  ← Material Symbol 网格
│                                                  │
│             [取消]          [创建并编辑]           │
└──────────────────────────────────────────────────┘
```

**分组 `/` 自动解析为多层目录：**

当用户输入 `游戏/暗区` 时，系统自动将 `/` 解析为目录层级：
- 一级分组：`游戏`
- 二级分组：`暗区`
- 工作流挂载在 `暗区` 下

```
输入 "游戏/暗区"  →  生成侧栏树：
  📂 工作流
    └ 📁 游戏
        └ 📁 暗区
            └ 🔵 新工作流    ← 新建的工作流
```

输入 `A/B/C` 则生成三层嵌套。纯 `/` 字符在 group 字段中直接保留，后端 `build_sidebar_tree()` 按 `/` 分割生成树。

常用图标预选列表：`sports_esports`, `account_tree`, `smart_toy`, `psychology`, `mic`, `document_scanner`, `camera`, `headset_mic`, `record_voice_over`, `terminal`, `hub`, `sensors`, `volume_up`, `history_edu`, `upload_file`

创建后自动打开工作流，进入**流程模式**。

---

## 3. 流程模式 / 编辑 双模式

> **流程模式**（默认）：打开工作流后默认进入，可查看完整管线，节点连线只读。点击 `[流程设置]` 进入编辑模式。
> **编辑模式**：可拖拽节点、创建连线、配置参数。点击 `[流程模式]` 返回只读查看。

### 3.1 模式对比

| 功能 | 流程模式（默认） | 编辑模式 |
|------|---------|---------|
| 节点可见 | ✓ | ✓ |
| 连线可见 | ✓ | ✓ |
| 端口圆点可见 | ✗ | ✓ (数据流/全部视图) |
| 节点可拖拽 | ✗ | ✓ |
| 右键菜单 | ✗ | ✓ |
| 悬浮工具面板 | ✗ | ✓ |
| 右侧详情/配置面板 | ✗ (不可打开) | ✓ (可打开) |
| 顶栏按钮 | `[流程设置]` | `[流程模式]` `[保存]` `[撤销]` `[重做]` |
| Delete 删除节点 | ✗ | ✓ |
| Ctrl+Z/Y | ✗ | ✓ |
| 连线点击删除 | ✗ | ✓ |

> **按钮逻辑**：
> - **流程模式** `[流程设置]`：点击即进入编辑模式（同时打开画布尺寸等流程级设置面板，或直接进入可编辑状态）
> - **编辑模式** `[流程模式]`：点击即退出编辑模式，返回流程模式查看管线

### 3.2 模式切换

**流程模式（默认）顶栏：** `[流程设置]`
**编辑模式顶栏：** `[流程模式]` `[保存状态指示器]` `[撤销]` `[重做]`

```html
<!-- 流程模式（默认） — 仅 [流程设置] 按钮，点击进入编辑模式 -->
<button class="top-btn primary-btn" onclick="enterEditMode()">
  <span class="material-symbols-outlined">tune</span> 流程设置
</button>

<!-- 编辑模式 — [流程模式] 退出 + 保存/撤销/重做 -->
<button class="top-btn ghost-btn" onclick="exitEditMode()">
  <span class="material-symbols-outlined">visibility</span> 流程模式
</button>
<span class="save-indicator">...</span>  ← 保存状态指示器
<button class="top-btn ghost-btn" onclick="undo()" :disabled="!canUndo">
  <span class="material-symbols-outlined">undo</span>
</button>
<button class="top-btn ghost-btn" onclick="redo()" :disabled="!canRedo">
  <span class="material-symbols-outlined">redo</span>
</button>
```

> **注意**：流程模式下的 `[流程设置]` 按钮使用 `primary-btn` 样式（`bg-primary text-on-primary`），作为主要操作入口在顶栏突出显示。编辑模式下的 `[流程模式]` 使用 `ghost-btn` 样式。

```
[流程设置] 样式:
  background: #adc7ff; color: #002e68; border: 1px solid #adc7ff;
  hover: background: #d8e2ff;

[流程模式] / [撤销] / [重做] 样式（ghost-btn）:
  background: transparent; color: #8b90a0; border: 1px solid #414754;
  hover: color: #c1c6d7; border-color: #8b90a0;
```

---

## 4. 悬浮工具面板

### 4.1 显示条件

**仅在编辑模式下显示**，流程模式完全不可见。

### 4.2 位置

悬浮于画布区域左侧，与底部缩放控制栏同级（z-50）：

```
位置：left: 272px (sidebar 256px + 16px), top: 72px (nav 56px + 16px)
宽度：200px
```

### 4.3 外观

```
┌──────────────────────┐
│ 工具面板        [−]  │  ← 可折叠/最小化
├──────────────────────┤
│ ── 输入 ──           │  ← 分组标题 (outline-variant/60, uppercase)
│ ┌──────────────────┐ │
│ │▌📤 上传图片   0↘2│ │  ← palette-card, 左侧 3px 颜色条
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │▌🎤 TS 音频输入 1↘1│ │
│ └──────────────────┘ │
│ ── 处理 ──           │
│ ┌──────────────────┐ │
│ │▌📄 OCR 识别   1↘1│ │  ← icon + 名称 + 端口数(入↘出)
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │▌🔗 ContextBld 4↘1│ │
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │▌🤖 LLM 生成   1↘1│ │
│ └──────────────────┘ │
│ ── 音频 ──           │
│ ┌──────────────────┐ │
│ │▌🎙 STT 监听   1↘1│ │
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │▌📋 STT History 1↘2│ │
│ └──────────────────┘ │
│ ── 输出 ──           │
│ ┌──────────────────┐ │
│ │▌🔊 TTS 合成   1↘1│ │
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │▌📢 TS 音频输出1↘1│ │
│ └──────────────────┘ │
└──────────────────────┘
  毛玻璃背景 (bg-slate-950/80 backdrop-blur-md)
  圆角 8px, border: outline-variant/50
```

### 4.4 palette-card 样式

```css
.palette-card {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 6px;
  cursor: grab; user-select: none;
  transition: all 0.15s;
  border: 1px solid rgba(65, 71, 84, 0.3);
  background: rgba(24, 28, 35, 0.6);
}
.palette-card:hover {
  background: rgba(28, 32, 39, 0.9);
  border-color: rgba(65, 71, 84, 0.6);
}
.palette-card:active {
  cursor: grabbing; transform: scale(0.96);
}
/* 左侧颜色条 */
.palette-card { border-left: 3px solid <node.color>; }
```

### 4.5 拖拽到画布

1. palette-card 上 mousedown → 开始拖拽
2. 创建 ghost 元素跟随鼠标（`position: fixed, z-index: 9999`）
3. ghost 内容：`icon + 节点名称`
4. ghost 进入画布区域 → 边框变绿（`#4edea3`）
5. mouseup 在画布上 → 计算画布坐标 → 创建新节点
6. mouseup 在画布外 → 取消，ghost 移除

```javascript
// 坐标转换（screen → canvas）
const canvas = document.getElementById('canvas-container');
const rect = canvas.getBoundingClientRect();
const x = (e.clientX - rect.left + canvas.scrollLeft) / zoom - halfNodeWidth;
const y = (e.clientY - rect.top + canvas.scrollTop) / zoom - halfNodeHeight;
```

---

## 5. 节点卡片

### 5.1 结构（与现有 `NodeCard.vue` 一致）

```
┌────────────────────────────────────────┐
│ ● InputPort ①              [②] 徽章 │ ← .workflow-badge, absolute top:-10px right:-10px
│ ● InputPort ②                        │
│                                      │
│ [icon] 节点标题    [状态标签] [●keyword]│ ← .node-header: flex, gap-2, px-3 py-2, border-b
├────────────────────────────────────────┤
│ [配置] [详情] [日志]                  │ ← .node-tab-bar: flex, border-b（仅 tabs.length > 0）
├────────────────────────────────────────┤
│                                      │ ← .node-body: p-3（无 tab）或 .node-tab-content（有 tab）
│  状态: ● 待命                        │   <slot> 默认插槽，由节点专属组件渲染
│  ┌──────────────────────────────────┐ │
│  │ ████████████░░░░░░ 45%          │ │   .progress-bar（仅 processing 状态）
│  └──────────────────────────────────┘ │
│                                      │
│                      ● OutputPort ① │ ← 输出端口，right: -7px
│                      ● OutputPort ② │
└────────────────────────────────────────┘
```

**与 `NodeCard.vue` 的对应关系：**

| 元素 | CSS class | Vue 实现 |
|------|----------|---------|
| 节点容器 | `.node-card` + `glass-node` | `position: absolute`, 毛玻璃, 圆角 8px |
| 步骤号徽章 | `.workflow-badge` | `<div v-if="stepNumber">` 绝对定位右上角 -10px |
| 输入端口 | `.io-port.input-port` | `<IOPort v-for="port in inputPorts" side="left">` |
| 输出端口 | `.io-port.output-port` | `<IOPort v-for="port in outputPorts" side="right">` |
| 节点头部 | `.node-header` | 包含 icon + title + status-badge + keyword-dot |
| Tab 栏 | `.node-tab-bar` | `<div v-if="tabs.length > 0">` 动态渲染 `.tab-btn` |
| Tab 内容 | `.node-tab-content` | `v-show="activeTab === tab.id"` |
| 默认 body | `.node-default-body` | `<slot>` 默认内容：状态行 + 进度条 |
| 状态点 | `.status-dot` | 颜色和动画由 `statusClass` 计算属性决定 |
| 进度条 | `.progress-bar` + `.progress-fill` | `v-if="nodeStatus === 'processing'"` |
| 关键词点 | `.keyword-dot` | `v-if="isListening"` |

### 5.2 样式

```css
.node-card {
  position: absolute;
  background: rgba(28, 32, 39, 0.92);      /* surface-container @ 92% */
  backdrop-filter: blur(12px);
  border-radius: 8px;
  border: 1px solid;
  z-index: 10;
  cursor: pointer;                         /* 编辑模式: move */
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  user-select: none;
}
.node-card:hover {
  transform: translateY(-2px);
  z-index: 20 !important;
}
.node-card.selected {
  border-color: #4a8eff !important;
  box-shadow: 0 0 16px rgba(74, 142, 255, 0.3);
}
```

### 5.3 边框颜色语义

| 状态 | 边框 | 说明 |
|------|------|------|
| 待命 (pending) | `border-outline-variant/50` | 默认 |
| 处理中 (processing) | `border: 2px solid primary/50 + node-pulse` | 蓝色脉冲 |
| 已完成 (completed) | `border-secondary/40` | 绿色 |
| 错误 (error) | `border-error/50` | 红色 |
| 监听中 (listening) | `border-primary/50 + keyword-dot` | 蓝色 + 关键词脉冲点 |
| 选中 (selected) | `border: 2px solid #4a8eff` | 亮蓝（覆盖状态色） |

### 5.4 节点宽度映射

| 节点 type | 宽度 | 说明 |
|-----------|------|------|
| `input_image`, `ocr`, `ts_input`, `tts`, `ts_output` | 220px | 简单节点 |
| `context_build`, `llm` | 250px | 中等节点 |
| `stt_history` | 280px | 双列节点 |
| `stt_listen` | 320px | 多 tab 节点 |

### 5.5 步骤号徽章

```css
.workflow-badge {
  position: absolute; top: -10px; right: -10px;
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: bold;
  font-family: 'Space Grotesk', sans-serif;
  z-index: 40; border: 2px solid; background: #10131b;
}
```

徽章数字使用 Unicode 带圈数字 `① ② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨` (U+2460-U+2468)，按节点在数组中顺序分配。

---

## 6. 端口圆点交互

### 6.1 显示规则

- **仅在编辑模式下显示**
- **事件流视图和数据流视图各自拥有对应的端口圆点交互**
- 输入端口在节点左侧 `left: -7px`
- 输出端口在节点右侧 `right: -7px`

### 6.2 端口默认位置（自动均匀分布）

端口不固定 top 值，而是根据端口数量**自动均匀分布**在节点卡片高度范围内：

**算法**：将节点卡片高度（含 header 约 40px + body 区）均分为 N+1 等份，端口位于等分点。

| 端口数 | 位置分布 | 示例 (节点高 140px) |
|--------|---------|-------------------|
| 1 个端口 | 1/2 = 中间 | top: 70px |
| 2 个端口 | 1/3, 2/3 | top: 42px, top: 84px |
| 3 个端口 | 1/4, 2/4, 3/4 | top: 30px, top: 60px, top: 90px |
| 4 个端口 | 1/5, 2/5, 3/5, 4/5 | top: 24px, top: 48px, top: 72px, top: 96px |

```javascript
function calculatePortPositions(portCount, nodeHeight) {
  // header ~40px, body padding ~12px → effective area ~nodeHeight - 52
  // 第一个端口从 header 下方开始
  const startY = 40;  // header 高度
  const areaHeight = nodeHeight - startY - 12;  // 减去上下 padding
  if (portCount <= 1) return [startY + areaHeight / 2];
  return Array.from({ length: portCount }, (_, i) =>
    startY + (areaHeight * (i + 1)) / (portCount + 1)
  );
}
```

各节点端口数及默认 top 值：

| 节点 type | 输入端口数 | 输入 top | 输出端口数 | 输出 top |
|-----------|-----------|---------|-----------|---------|
| `input_image` | 0 | — | 2 | 56, 112 |
| `ocr` | 1 | 92 | 1 | 92 |
| `ts_input` | 1 | 92 | 1 | 92 |
| `stt_listen` | 1 | 92 | 1 | 92 |
| `stt_history` | 1 | 92 | 2 | 56, 112 |
| `context_build` | 4 | 27, 54, 81, 108 | 1 | 92 |
| `llm` | 1 | 92 | 1 | 92 |
| `tts` | 1 | 92 | 1 | 92 |
| `ts_output` | 1 | 92 | 1 | 92 |

### 6.3 端口基础样式

```css
.io-port {
  position: absolute; width: 14px; height: 14px; border-radius: 50%;
  border: 2.5px solid #8b90a0; background: #10131b;
  z-index: 35; cursor: pointer;          /* 编辑模式: crosshair */
  transition: all 0.2s ease;
}
.io-port:hover { transform: scale(1.5); z-index: 60; }
.io-port.input-port  { left: -7px; }
.io-port.output-port { right: -7px; }
```

### 6.4 端口手动拖动位置

用户可**手动拖动**端口圆点沿节点侧边垂直移动，改变端口在节点上的位置。

- 在端口上按下并垂直拖拽 → 端口沿节点侧边上下移动
- 移动范围：节点 header 下方到节点底部（不可拖出节点区域）
- mouseup 时保存端口新位置到 `port.position.top`
- 拖动时连线实时跟随新位置

```javascript
// 端口拖动
function startPortDrag(e, nodeId, portId, side) {
  const portEl = e.target.closest('.io-port');
  const nodeEl = portEl.closest('.node-card');
  const nodeRect = nodeEl.getBoundingClientRect();
  const startY = e.clientY;
  const startTop = parseInt(portEl.style.top);

  function onMove(ev) {
    const deltaY = ev.clientY - startY;
    const newTop = Math.max(28, Math.min(nodeRect.height - 20, startTop + deltaY));
    portEl.style.top = newTop + 'px';
    renderConnections(); // 连线跟随
  }

  function onUp() {
    // 持久化新位置
    savePortPosition(nodeId, portId, parseInt(portEl.style.top));
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  }

  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
}
```

### 6.5 端口视觉状态

| 状态 | class | border-color | background | shadow |
|------|-------|-------------|-----------|--------|
| 未连接 | `.disconnected` | `#8b90a0` | `#10131b` | none |
| 已连接 | `.connected` | `#4edea3` | `rgba(78,222,163,0.12)` | `0 0 8px rgba(78,222,163,0.3)` |
| 数据流通 | `.flowing` | `#4a8eff` | `rgba(74,142,255,0.18)` | `0 0 12px rgba(74,142,255,0.5)` + portFlowPulse |
| 拖拽兼容目标 | `.drag-over.valid` | `#4edea3` | `rgba(78,222,163,0.3)` | `0 0 16px rgba(78,222,163,0.6)` + scale(1.8) |
| 拖拽不兼容目标 | `.drag-over.invalid` | `#ffb4ab` | `rgba(255,180,171,0.3)` | `0 0 16px rgba(255,180,171,0.6)` + scale(1.8) |

### 6.6 输出端口 — 拖拽连线（数据流 + 事件流视图通用）

从输出端口 **mousedown + 拖拽**：

1. 创建临时 SVG `<line>` 跟随鼠标
2. 起点 = 源端口圆心（屏幕坐标）
3. 检测鼠标悬停在输入端口上 → 加视觉反馈
4. mouseup 在兼容端口上 → 创建连线
5. mouseup 在空白处 → 取消

**数据流视图**：拖拽创建 `data` 类型连线（绿色虚线）
**事件流视图**：拖拽创建 `event` 类型连线（蓝色实线箭头）

```
临时线: stroke="#4a8eff" stroke-width="2.5" stroke-dasharray="8 4"
```

### 6.7 输入端口 — 点击弹出配置面板

**数据流视图下**，点击（非拖拽）输入端口圆点，弹出小型浮动配置面板：

```
┌───────────────────────────────────┐
│ ● 端口: 识别文本                   │
│   数据类型: String                │
│ ───────────────────────────────── │
│ 输入来源:                          │
│   ◉ 连线数据（从上游获取）          │
│   ○ 本节点参数                     │
│   ○ 手动默认值                     │
│ ───────────────────────────────── │
│                                   │
│ [连线获取模式 — 已连线时显示]        │
│   当前连线:                        │
│     stt_listen.stt-out → 此端口    │
│   [移除连线]                       │
│                                   │
│ [本节点参数模式 — 选中时显示]        │
│   参数路径:                        │
│   config.[▼ 下拉选择参数名]        │
│   预览: (当前值)                    │
│                                   │
│ [手动默认值模式 — 选中时显示]        │
│   默认值:                          │
│   ┌─────────────────────────────┐ │
│   │ 输入固定文本或数值...         │ │
│   └─────────────────────────────┘ │
│                                   │
│ ───────────────────────────────── │
│            [应用]  [关闭]          │
└───────────────────────────────────┘
```

**三种输入来源详解：**

| 来源 | 说明 | 数据存储 |
|------|------|---------|
| **连线数据** | 从上游节点的输出端口通过连线获取数据 | `source.type = "connection"` |
| **本节点参数** | 引用当前节点 config 中的某个字段值 | `source.type = "param"`, `source.param_path = "config.xxx"` |
| **手动默认值** | 用户直接输入的固定内容，不依赖其他节点 | `source.type = "default"`, `source.value = "..."` |

选择「本节点参数」或「手动默认值」时，该端口的已有连线自动移除。

### 6.8 输出端口 — 点击查看下游

**数据流视图下**，点击（非拖拽）已连线的输出端口：

```
┌───────────────────────────────┐
│ ● 端口: OCR文本                │
│   数据类型: String             │
│ ───────────────────────────── │
│ 下游连线:                       │
│   → context_build.ctx-in2     │
│   → [移除连线]                  │
│ ───────────────────────────── │
│          [关闭]                 │
└───────────────────────────────┘
```

### 6.9 事件流视图下的端口交互

事件流视图也显示端口圆点，但交互侧重触发/事件关系：
- 输出端口（类型为 `event`）可拖拽创建事件连线
- 输入端口（类型为 `event`）可点击查看上游触发源
- 事件端口不显示「手动默认值」和「本节点参数」选项（事件不支持手动来源）

### 6.10 端口面板技术细节

- 面板使用 `position: fixed`（基于端口屏幕坐标定位）
- z-index: 150（高于节点卡片、连线 SVG）
- 点击面板外部或按 Escape 关闭
- 毛玻璃背景，圆角 8px，border outline-variant

---

## 7. 数据类型兼容规则

连线创建时校验端口数据类型：

| 输出 data_type | 可连接输入 data_type | 示例 |
|---------------|---------------------|------|
| `image` | `image` | 上传图片 → OCR |
| `audio` | `audio` | TTS 合成 → TS 音频输出 |
| `string` | `string`, `string_array` | OCR 文本 → ContextBuild |
| `string_array` | `string_array`, `messages` | STT History → ContextBuild |
| `messages` | `messages` | ContextBuild → LLM |
| `event` | `event` 连线 type | 仅用于事件流（trigger），不参与数据流校验 |

跨类型连接直接拒绝（视觉红色提示 + 不可松手创建）。

---

## 8. 连线渲染

### 8.1 SVG 结构

```svg
<svg class="connections-svg" width="1700" height="1250">
  <defs> (箭头标记) </defs>

  <!-- 数据流连线 -->
  <g class="data-only">
    <g class="conn-hit-area" data-conn-id="conn_xxx">
      <path d="M ... C ..." fill="none" stroke="#4edea3" stroke-width="2.5"
            stroke-dasharray="10 5" class="flow-line"
            marker-end="url(#arrowData)"/>
      <rect class="conn-label-bg" .../>
      <text ...>图片数据 (PNG/JPG)</text>
    </g>
  </g>

  <!-- 事件流连线 -->
  <g class="event-only">
    <g class="conn-hit-area" data-conn-id="conn_xxx">
      <path d="..." fill="none" stroke="#adc7ff" stroke-width="2.5"
            marker-end="url(#arrowEvent)"/>
      <rect .../><text ...>触发OCR识别</text>
    </g>
  </g>
</svg>
```

### 8.2 连线类型

| 类型 | 颜色 | 线宽 | 线型 | 箭头 | CSS class |
|------|------|------|------|------|-----------|
| 数据流（静态） | `#4edea3` (secondary) | 2.5 | `dasharray: 10 5` | arrowData | `.flow-line` |
| 数据流（活跃） | `#4a8eff` (primary-container) | 2.5 | 实线 | arrowDataFlow | `.flow-line` |
| 事件流 | `#adc7ff` (primary) | 2.5 | 实线 | arrowEvent | — |
| 循环回路 | `#4edea3` (secondary) | 1.8 | `dasharray: 6 6` | — | `.loop-line` opacity: 0.45 |

### 8.3 路径算法

```javascript
function computePath(fromX, fromY, toX, toY) {
  const yDiff = Math.abs(fromY - toY);
  if (yDiff < 80) {
    const midX = (fromX + toX) / 2;
    return `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`;
  } else {
    const cpOffset = Math.abs(fromX - toX) * 0.5;
    return `M ${fromX} ${fromY} C ${fromX + cpOffset} ${fromY}, ${toX - cpOffset} ${toY}, ${toX} ${toY}`;
  }
}
```

### 8.4 连线标签

- 位置：路径中点
- 文字：输出端口的 `label` 字段
- 背景：`fill: rgba(11, 14, 22, 0.92)` 圆角矩形
- 字体：`Space Grotesk`, `font-size: 10px`, `font-weight: bold`

### 8.5 连线交互

- **hover**：连线加粗，提示可点击
- **click**：选中连线 → 高亮 → 可按 Delete 删除
- **右键**：弹出 `[删除连线]` 菜单

---

## 9. 右侧详情面板

### 9.1 显示条件

**仅在编辑模式下可用**。流程模式下右侧面板不显示、不响应双击/单击打开。

### 9.2 打开方式（编辑模式）

- 双击节点卡片
- 或单击节点卡片 → 右侧面板打开

### 9.3 面板外观

```
┌──────────────────────────────┐
│ [icon] 节点名称        [✕]   │ ← header: p-4, border-b, flex
├──────────────────────────────┤
│ [配置] [详情] [日志] [全文]   │ ← tab bar
├──────────────────────────────┤
│   (可滚动 tab 内容)           │ ← flex-1, overflow-y-auto
├──────────────────────────────┤
│     [取消]      [保存配置]     │ ← footer
└──────────────────────────────┘
```

面板固定于右侧：`position: fixed; right: 0; top: 56px; bottom: 32px; width: 320px; background: #020617;`

### 9.4 各 Tab 内容

#### Config tab（可编辑）

| 节点 type | 配置项 | 控件类型 |
|-----------|--------|---------|
| `input_image` | 节点名称 | text input |
| `ocr` | 引擎 (easyocr / paddleocr)、识别语言 | chip toggle |
| `stt_listen` | 引擎 (sensevoice / whisper / minimax)、关键词列表、采样率 | chip toggle + tag input |
| `stt_history` | 最大保留条数 | range slider |
| `context_build` | 包含模块 | chip toggle (多选) |
| `llm` | **skill_prompt** (textarea)、模型、Temperature、Max Tokens | textarea + chip toggle + range slider |
| `tts` | 引擎、音色、语速 | chip toggle + select + range slider |
| `ts_output` | 播放模式、自动循环 | chip toggle |

#### Detail tab（只读）

显示节点信息、输入/输出端口列表及连接状态。

#### Log tab（只读）

实时日志区，格式 `[HH:MM:SS] 消息`，颜色按级别分，FIFO 上限 200 条。

#### Fulltext tab（仅 `stt_listen`，只读）

运行时累积的完整识别文本。

---

## 10. 流程设置（画布尺寸 + 编辑入口）

### 10.1 入口

流程模式下点击顶栏 `[流程设置]` 即**进入编辑模式**。进入编辑模式后，画布尺寸等流程级配置可在以下位置调整：

- 右侧详情面板（无节点选中时）：显示流程级设置
- 或通过右键画布空白区域 → 「画布设置」

### 10.2 画布尺寸设置

```
┌──────────────────────────────┐
│ ⚙ 画布设置                    │
│                              │
│ 画布宽度  [____1700____] px  │
│ 画布高度  [____1250____] px  │
│                              │
│         [取消]    [保存]      │
└──────────────────────────────┘
```

**仅含画布尺寸**。skill_prompt 属于 LLM 节点的 config。

### 10.3 与 `[流程设置]` 按钮的关系

| 模式 | 按钮 | 行为 |
|------|------|------|
| 流程模式（默认） | `[流程设置]` | 点击进入编辑模式 |
| 编辑模式 | `[流程模式]` | 点击返回流程模式（自动保存） |

### 10.4 按钮样式

流程模式下的 `[流程设置]` 使用 `primary-btn` 突出样式（见 §3.2）。

---

## 11. 连线管理

### 11.1 创建连线

从输出端口拖拽到输入端口（见 §6.6），系统自动判断：
- 端口 data_type 是 `event` → 创建 `event` 类型连线
- 其他 → 创建 `data` 类型连线

### 11.2 删除连线

| 方式 | 操作 |
|------|------|
| 点击连线 + Delete 键 | 点击 SVG 路径选中 → 按 Delete |
| 点击连线 + 右键菜单 | 右键 → `[删除连线]` |
| 端口面板移除 | 点击输入端口 → 面板 `[移除连线]` |

### 11.3 校验规则

- from_port 必须在 from_node 的输出端口列表中
- to_port 必须在 to_node 的输入端口列表中
- data_type 必须兼容（见 §7）
- 禁止自身连接、闭环、重复连线

---

## 12. 视图切换

### 12.1 控制栏

位置：画布左下角，与缩放控制合并一行

```
[全部] [数据流] [事件流]  |  [-] [100%] [+] [适应]
```

### 12.2 三种视图

| 视图 | `data-flow` attr | 数据连线+数据端口 | 事件连线+事件端口 | 说明 |
|------|-----------------|------------------|------------------|------|
| 全部 | `all` | 显示 | 显示 | 所有连线+所有端口 |
| 数据流 | `data` | 显示 | **隐藏** | 仅数据连线+数据端口可交互 |
| 事件流 | `event` | **隐藏** | 显示 | 仅事件连线+事件端口可交互 |

### 12.3 两种端口体系

| 端口 data_type | 所属视图 | 交互功能 |
|---------------|---------|---------|
| image, audio, string, string_array, messages | **数据流** | 拖拽创建数据连线、点击配置输入来源 |
| event | **事件流** | 拖拽创建事件连线、查看触发关系 |

---

## 13. 键盘快捷键

| 快捷键 | 作用 | 条件 |
|--------|------|------|
| `Ctrl+Z` | 撤销 | 编辑模式 |
| `Ctrl+Y` | 重做 | 编辑模式 |
| `Delete` / `Backspace` | 删除选中节点或连线 | 编辑模式 + 有选中项 |
| `Ctrl+C` | 复制选中节点 | 编辑模式 |
| `Ctrl+V` | 粘贴节点 | 编辑模式 |
| `Ctrl+N` | 新建工作流 | 全局 |
| `Escape` | 取消选中/关闭面板/取消拖拽 | 全局 |
| `Ctrl+S` | 手动保存 | 编辑模式 |
| 鼠标中键拖拽 | 平移画布 | 画布区域 |
| 滚轮 | 缩放画布 | 画布区域 |
| 双击节点 | 打开详情面板 | **仅编辑模式** |

---

## 14. 撤销 / 重做

### 14.1 操作记录格式

```json
{
  "action": "node.move",
  "forward": { "node_id": "ocr_01", "new_position": { "x": 250, "y": 400 } },
  "reverse": { "node_id": "ocr_01", "old_position": { "x": 40, "y": 300 } }
}
```

### 14.2 可撤销操作

| action | forward | reverse |
|--------|---------|---------|
| `node.create` | 创建节点 | 删除节点 + 关联连线 |
| `node.delete` | 删除节点 | 恢复节点 + 关联连线 |
| `node.move` | 新位置 | 旧位置 |
| `node.update_config` | 新 config | 旧 config |
| `node.rename` | 新名称 | 旧名称 |
| `port.move` | 新 top 值 | 旧 top 值 |
| `connection.create` | 创建连线 | 删除连线 |
| `connection.delete` | 删除连线 | 恢复连线 |

栈上限 100 条，新操作清空 redo 栈。

---

## 15. 保存机制

### 15.1 自动保存

| 触发操作 | 策略 |
|---------|------|
| node.create / node.delete / node.move | 即时保存 |
| node.update_config (switch/toggle/select) | 即时保存 |
| node.update_config (text input) | 500ms debounce |
| port.move (端口拖动) | dragend 即时保存 |
| connection.create / connection.delete | 即时保存 |

### 15.2 保存状态指示器

| 状态 | 图标 | 颜色 |
|------|------|------|
| 已保存 | `cloud_done` | `#4edea3` |
| 保存中 | `sync` (animate-spin) | `#ffb695` |
| 未保存 | `cloud_off` | `#8b90a0` |

---

## 16. 节点类型完整定义

### 16.1 总览

共 9 种节点（与后端 `NodeRegistry` 中 `_TYPE_METADATA` 一致）：

| # | type | 名称 | 颜色 | 宽度 | 类别 | tabs |
|---|------|------|------|------|------|------|
| ① | `input_image` | 上传图片 | secondary | 220px | 输入 | — |
| ② | `ocr` | OCR 识别 | secondary | 220px | 处理 | config, detail, log |
| ③ | `ts_input` | TS 音频输入 | secondary | 220px | 输入 | config, detail |
| ④ | `stt_listen` | STT 持续监听 | primary | 320px | 音频 | config, detail, log, fulltext |
| ⑤ | `stt_history` | STT History·关键词判断 | tertiary | 280px | 音频 | config, detail, log |
| ⑥ | `context_build` | ContextBuild | primary | 250px | 处理 | config, detail, log |
| ⑦ | `llm` | LLM 生成 | primary | 250px | 处理 | config, detail, log |
| ⑧ | `tts` | TTS 合成 | outline | 220px | 输出 | config, detail, log |
| ⑨ | `ts_output` | TS 音频输出 | secondary | 220px | 输出 | — |

### 16.2 完整端口定义（含默认 top 值）

端口 top 按 1/(N+1), 2/(N+1) ... 均匀分布（基于节点高度 ~140px）：

| # | type | 输入端口 (left) | 输出端口 (right) |
|---|------|----------------|-----------------|
| ① | `input_image` | — | `img-out` (image, top:56), `trigger-out` (event, top:112) |
| ② | `ocr` | `ocr-in` (image, top:92) | `ocr-out` (string, top:92) |
| ③ | `ts_input` | `ts-in` (event, top:92) | `ts-out` (audio, top:92) |
| ④ | `stt_listen` | `stt-in` (audio, top:92) | `stt-out` (string, top:92) |
| ⑤ | `stt_history` | `hist-in` (string, top:92) | `hist-out` (string_array, top:56), `hist-trigger` (event, top:112) |
| ⑥ | `context_build` | `ctx-in1` (string, top:27), `ctx-in2` (string, top:54), `ctx-in3` (string_array, top:81), `ctx-in4` (string_array, top:108) | `ctx-out` (messages, top:92) |
| ⑦ | `llm` | `llm-in` (messages, top:92) | `llm-out` (string, top:92) |
| ⑧ | `tts` | `tts-in` (string, top:92) | `tts-out` (audio, top:92) |
| ⑨ | `ts_output` | `out-in` (audio, top:92) | `out-done` (event, top:92) |

### 16.3 默认配置

```json
{
  "input_image": { "auto_trigger": true },
  "ocr": { "engine": "easyocr", "language": ["zh"], "confidence_threshold": 0.3 },
  "ts_input": { "sample_rate": 16000, "channels": 1 },
  "stt_listen": { "engine": "sensevoice", "keywords": ["求助", "集合", "撤退"], "sample_rate": 16000 },
  "stt_history": { "max_entries": 20 },
  "context_build": { "include_ocr": true, "include_stt": true, "max_context_length": 4096 },
  "llm": { "model": "gpt-4-turbo", "temperature": 0.7, "max_tokens": 2048, "streaming": true, "skill_prompt": "" },
  "tts": { "engine": "edge", "voice": "zh-CN-YunxiNeural", "speed": 1.0 },
  "ts_output": { "play_mode": "segment", "auto_loop": true }
}
```

---

## 17. 设计规范引用

本编辑器遵循以下已有规范：

| 文档 | 内容 |
|------|------|
| [ui-style-guide.md](./ui-style-guide.md) | 颜色系统（MD3 暗色）、字体（Inter + Space Grotesk）、间距圆角、毛玻璃效果、组件规范、动画关键帧、SVG 连线标记 |
| [websocket-protocol.md](./websocket-protocol.md) | 信封消息格式（msg_id/flow_id/type/action/params/ts）、全部 action 定义、NodeTypeDef/FlowDef/ConnectionDef 数据模型、Binary frame 文件上传 |
| [architecture-spec.md](./architecture-spec.md) | 前后端职责边界（后端持有全部状态）、生命周期序列、undo/redo 机制、文件上传流程、编辑/执行互斥锁 |
| [pipeline-prototype_flow.html](../frontend/docs/pipeline-prototype_flow.html) | 现有静态原型（视觉参考，完整 9 节点管线，1223 行） |
