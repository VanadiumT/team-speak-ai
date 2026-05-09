# 节点交互设计规范

> 定义统一的节点卡片、IO 端口、右侧面板、标签页系统的交互设计与视觉规范。
> 覆盖「暗区竞标赛」完整流程中每个节点的具体设计。
> 与 [node-system-design.md](./node-system-design.md)、[pipeline-editor-spec.md](./pipeline-editor-spec.md)、[view-mode-and-features-spec.md](./view-mode-and-features-spec.md)、[ui-style-guide.md](./ui-style-guide.md) 互补。

---

## 目录

1. [设计总纲：统一设计模式](#1-设计总纲统一设计模式)
2. [统一页面布局](#2-统一页面布局)
3. [统一节点卡片设计](#3-统一节点卡片设计)
4. [统一 IO 端口设计](#4-统一-io-端口设计)
5. [统一右侧面板设计](#5-统一右侧面板设计)
6. [流程走查：暗区竞标赛](#6-流程走查暗区竞标赛)
7. [节点逐一设计](#7-节点逐一设计)
8. [组件实现指南](#8-组件实现指南)

---

## 1. 设计总纲：统一设计模式

### 1.1 核心公式

```
节点卡片 = 通用壳 (NodeCard) + 类型内容注入 (NodeBody)
右侧面板 = 通用面板壳 (DetailPanel) + Tab 内容注入
IO 端口 = 通用端口壳 (IOPort) + 点击弹窗 (PortPopover)
```

**壳负责**：布局、边框状态色、动画、拖拽、端口渲染、Tab 栏骨架。
**内容负责**：节点 body 区根据 `node.type` + `node.status` + `activeTab` 渲染不同组件。

### 1.2 双模式行为矩阵

| 维度 | 流程模式 (Flow Mode) | 编辑模式 (Edit Mode) |
|------|---------------------|---------------------|
| **节点 body** | 显示执行状态 + 最近输出摘要（紧凑） | 显示配置表单（可编辑） |
| **端口圆点** | 仅"活"端口可见，点击查看只读弹窗 | 全部端口可见，点击可配置 |
| **Tab 栏** | 固定显示 detail（不可切换） | 可切换 config/detail/log |
| **右侧面板** | 只读（detail + log + IO 数据） | 可编辑 config + 只读 detail/log |
| **连线交互** | 悬停高亮，不可选中/删除 | 可选中/删除 |
| **节点拖拽** | 禁止 | 允许 |
| **右键菜单** | 无 | 节点操作菜单 |

### 1.3 五个运行时状态的视觉映射

| 状态 | 边框 | 状态点 | body 内容 | 动画 |
|------|------|--------|----------|------|
| **PENDING** | `outline-variant/50` | 灰点 | 等待触发提示 | 无 |
| **PROCESSING** | `primary/50` + 2px | 蓝点呼吸 | 进度条/流式文本 | `nodePulse` |
| **COMPLETED** | `secondary/40` | 绿点 | 输出数据摘要 | 无 |
| **ERROR** | `error/50` | 红点 | 错误信息 | 无 |
| **LISTENING** | `primary/50` | 蓝点呼吸 + 关键词脉冲 | 实时识别文本 | `nodePulse` + `keywordPulse` |

---

## 2. 统一页面布局

### 2.1 整体布局（不变）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ① Top Nav Bar (56px)                                                     │
├────────┬───────────────────────────────────────────────┬──────────────────┤
│②Sidebar│            ③ Canvas                           │④ Right Panel     │
│256px   │                                               │ 320px            │
│        │  ┌─────────┐     ┌─────────┐                │ (条件显示)        │
│        │  │ ①上传图片│────→│ ② OCR   │                │                  │
│        │  └─────────┘     └─────────┘                │                  │
│        │      ⑤ NodePalette (仅 Edit Mode)           │                  │
│        │                                              │                  │
│        │  ⑥ Canvas Controls                          │                  │
├────────┴───────────────────────────────────────────────┴──────────────────┤
│ ⑦ Bottom Status Bar (32px)                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 流程模式 vs 编辑模式——区域差异

| 区域 | 流程模式 | 编辑模式 |
|------|---------|---------|
| ① Top Nav | `[运行]` + `[流程设置]` | `[流程模式]` + 保存指示器 + `[撤销]` `[重做]` |
| ② Sidebar | 始终全功能 | 始终全功能 |
| ③ Canvas | 可平移/缩放，不可编辑 | 可平移/缩放 + 右键菜单 |
| ④ Right Panel | 单击节点打开（只读） | 双击节点打开（可编辑） |
| ⑤ NodePalette | 隐藏 | 显示 |
| ⑥ Canvas Controls | 始终显示 | 始终显示 |
| ⑦ Bottom Bar | 始终显示 | 始终显示 |

---

## 3. 统一节点卡片设计

### 3.1 卡片结构

```
┌──────────────────────────────────────────┐
│ ● port-1                    [②] 徽章    │  ← 输入端口 (left: -7px)
│ ● port-2                                │
│                                         │
│ [icon] 节点标题         [状态标签] [KW]  │  ← .node-header (px-3 py-2, border-b)
├──────────────────────────────────────────┤
│ [配置] [详情] [日志] [全文]              │  ← .node-tab-bar (仅 tabs.length > 0 且可切换)
├──────────────────────────────────────────┤
│                                         │  ← .node-body (p-3)
│  ┌─ Flow Mode body ──────────────────┐  │
│  │ ● 状态: 监听中                     │  │     状态行 + 输出摘要
│  │ 最近输出: "A点有敌人，注意"        │  │
│  └────────────────────────────────────┘  │
│  ── 或 ──                               │
│  ┌─ Edit Mode body ──────────────────┐  │
│  │ 引擎: [sensevoice ▾]              │  │     配置表单
│  │ 关键词: [求助] [集合] [撤退]  [+]  │  │
│  └────────────────────────────────────┘  │
│                                         │
│                      ● port-3           │  ← 输出端口 (right: -7px)
│                      ● port-4           │
└──────────────────────────────────────────┘
```

### 3.2 卡片 CSS 规范

```css
.node-card {
  position: absolute;
  background: rgba(28, 32, 39, 0.92);
  backdrop-filter: blur(12px);
  border-radius: 8px;
  border: 1px solid;
  z-index: 10;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  user-select: none;
}

/* 宽度映射 */
.node-card.w-220 { width: 220px; }  /* input_image, ocr, ts_input, tts, ts_output */
.node-card.w-250 { width: 250px; }  /* context_build, llm */
.node-card.w-280 { width: 280px; }  /* stt_history */
.node-card.w-320 { width: 320px; }  /* stt_listen */
```

### 3.3 两种模式下的 body 内容

**流程模式 body**（不可编辑，显示执行信息）：

```
┌────────────────────────────────┐
│ ● 状态: 监听中                  │  ← 状态点 + 状态文本
│                                │
│ 关键词: [求助] [集合] [撤退]    │  ← 配置摘要（标签）
│ 引擎: sensevoice               │
│                                │
│ ── 最近输出 ──                 │
│ "A点有敌人，注意"              │  ← 最后一次有效输出
│ 置信度: 0.92                   │
│                                │
│ 触发次数: 12                   │  ← 统计信息
│ 累积历史: 47 条                │
└────────────────────────────────┘
```

**编辑模式 body**（可编辑配置表单，根据 `activeTab` 切换）：

```
┌────────────────────────────────┐
│ ── 配置 ──                     │
│ 引擎: [sensevoice ▾]           │
│ 采样率: [16000]                │
│ 关键词:                        │
│   [求助] [×]                   │  ← 可删除标签
│   [集合] [×]                   │
│   [+ 添加]                     │  ← 添加新关键词
└────────────────────────────────┘
```

### 3.4 Tab 栏行为

| 模式 | Tab 栏行为 |
|------|-----------|
| **流程模式** | 固定显示 `detail`（不可切换），或无 Tab 栏时直接显示 detail body |
| **编辑模式** | 可切换，显示所有 tab（config/detail/log/fulltext） |

**Tab 切换逻辑**：
- 流程模式：`activeTab` 强制锁定为 `"detail"`
- 编辑模式：用户自由切换，默认打开 `"config"`（如果有）

### 3.5 节点 body 组件注册

每种节点类型对应一个 Vue 组件，负责渲染 body 区内容：

```js
// components/pipeline/nodes/registry.js
export const nodeComponentRegistry = {
  input_image:   () => import('./InputImageNode.vue'),
  ocr:           () => import('./OcrNode.vue'),
  stt_listen:    () => import('./STTListenNode.vue'),
  stt_history:   () => import('./STTHistoryNode.vue'),
  context_build: () => import('./ContextBuildNode.vue'),
  llm:           () => import('./LLMNode.vue'),
  tts:           () => import('./TTSNode.vue'),
  ts_output:     () => import('./TSOutputNode.vue'),
  ts_input:      () => import('./TSInputNode.vue'),
}
```

**body 组件接收的 props**：

```ts
interface NodeBodyProps {
  node: NodeDefinition          // 节点完整数据
  nodeType: NodeTypeDef         // 类型元数据（端口、tab、默认配置）
  status: string                // pending | processing | completed | error | listening
  activeTab: string             // config | detail | log | fulltext
  editMode: boolean             // true = 可编辑配置, false = 只读
  summary: string               // 运行时摘要
  progress: number | null       // 进度 0-1
  data: Record<string, any>     // 运行时产出数据
  config: Record<string, any>   // 节点可编辑配置
  logs: LogEntry[]              // 日志条目
}
```

---

## 4. 统一 IO 端口设计

### 4.1 端口视觉规范

```css
.io-port {
  position: absolute;
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2.5px solid;
  background: #10131b;
  z-index: 35;
  cursor: pointer;
  transition: all 0.2s ease;
}

/* 端口状态色 */
.io-port.disconnected { border-color: #8b90a0; background: #10131b; }
.io-port.connected    { border-color: #4edea3; background: rgba(78,222,163,0.12); box-shadow: 0 0 8px rgba(78,222,163,0.3); }
.io-port.flowing      { border-color: #4a8eff; background: rgba(74,142,255,0.18); box-shadow: 0 0 12px rgba(74,142,255,0.5); animation: portFlowPulse 1.5s infinite; }
.io-port.has-value    { border-color: #adc7ff; background: rgba(173,199,255,0.12); }  /* 有数据但非连线来源 */

/* 端口数据类型图标（在 port 内部或旁边） */
.io-port[data-type="event"]::after { content: "◆"; font-size: 6px; }  /* 菱形 = 事件端口 */
.io-port[data-type="audio"]::after { content: "♪"; }
```

### 4.2 端口可见性规则

| 条件 | 流程模式 | 编辑模式 |
|------|---------|---------|
| `visibility = always` 且有数据来源 | **可见** | 可见 |
| `visibility = always` 但无数据来源 | **隐藏**（"死"端口） | 可见（灰色提醒） |
| `visibility = on-demand` 且有数据来源 | **可见** | 用户通过 "+" 露出的可见 |
| `visibility = on-demand` 但无数据来源 | **隐藏** | 隐藏（可在 "+" 菜单中露出） |

> **"有数据来源"** = 端口满足以下任一：有连线 / 配置了固定值 / 引用了流程参数 / 有模板预设默认值 / 运行时收到数据。

### 4.3 端口点击交互

#### 流程模式——点击端口（只读弹窗）

```
┌──────────────────────────────┐
│ 端口: stt-out                │
│ 类型: string                 │
│                              │
│ 数据来源: 连线 ← 当前         │
│ 上游: (本节点产出)            │
│                              │
│ ── 最近输出值 ──              │
│ "A点有敌人，注意"            │  ← 运行时最近一次产出
│ 更新于: 14:23:05             │
│                              │
│ 下游连线:                     │
│ → stt_history.hist-in        │
│                              │
│           [关闭]              │
└──────────────────────────────┘
```

#### 编辑模式——点击输入端口（配置弹窗）

```
┌──────────────────────────────┐
│ 端口: ctx-in-stt             │
│ 类型: string                 │
│ 状态: 已连线                  │
│                              │
│ 数据来源:                     │
│  ● 连线                      │  ← 当前生效（有连线时锁定此项）
│     stt_listen.text-out      │
│  ○ 流程参数                   │
│  ○ 固定值                     │
│  ○ 节点属性                   │
│                              │
│ [断开连线后可选其他来源]      │
│                              │
│           [关闭]              │
└──────────────────────────────┘

无连线时：
┌──────────────────────────────┐
│ 端口: ctx-in-stt             │
│ 类型: string                 │
│ 状态: 无连线                  │
│                              │
│ 数据来源:                     │
│  ○ 连线                      │
│  ● 流程参数                   │  ← 可切换
│    变量名: stt_last_text     │
│  ○ 固定值                     │
│    值: [________________]    │
│  ○ 默认值                     │
│    "你是TS语音助手..."        │
│                              │
│ 多源合并: [关闭]              │
│                              │
│        [保存]  [关闭]         │
└──────────────────────────────┘
```

#### 编辑模式——点击输出端口（下游查看）

```
┌──────────────────────────────┐
│ 端口: text-out               │
│ 类型: string                 │
│                              │
│ 下游连线:                     │
│ → stt_history.hist-in        │
│   [移除连线]                  │
│ → context_build.ctx-in2      │
│   [移除连线]                  │
│                              │
│           [关闭]              │
└──────────────────────────────┘
```

### 4.4 端口拖拽连线

仅在编辑模式下：
- **数据端口** (`image`/`audio`/`string`/`string_array`/`messages`)：拖拽创建 `data` 类型连线
- **事件端口** (`event`)：拖拽创建 `event` 类型连线
- 临时线：`stroke="#4a8eff" stroke-width="2.5" stroke-dasharray="8 4"`
- 兼容端口高亮绿色，不兼容红色
- 松手在有效目标 → 创建连线；松手在空白 → 取消

---

## 5. 统一右侧面板设计

### 5.1 面板结构

```
┌──────────────────────────────────┐
│ [icon] 节点标题            [✕]   │  ← Header (p-4, border-b)
│ 类型: STT 持续监听               │
│ 状态: ● 监听中                   │
├──────────────────────────────────┤
│ [配置] [详情] [IO数据] [日志]    │  ← Tab bar
├──────────────────────────────────┤
│                                  │  ← Content (flex-1, overflow-y-auto, p-4)
│  (各 tab 内容，见下方)            │
│                                  │
├──────────────────────────────────┤
│          [取消]    [保存配置]     │  ← Footer (仅 Edit Mode + Config tab 显示)
└──────────────────────────────────┘
```

面板固定于右侧：`position: fixed; right: 0; top: 56px; bottom: 32px; width: 320px; background: #020617; z-index: 30;`

### 5.2 Tab 定义与使用场景

| Tab | 用途 | 流程模式 | 编辑模式 |
|-----|------|---------|---------|
| **配置** (config) | 节点业务参数编辑 | 只读显示 | **可编辑** |
| **详情** (detail) | 节点状态 + 输出摘要 | 只读（动态更新） | 只读 |
| **IO数据** (io-data) | 最近一次执行各端口的实际输入/输出值 | 只读 | 只读 |
| **日志** (log) | 节点执行日志 | 只读（实时追加） | 只读 |

> **新增 `IO数据` tab**：与 `detail` 分开。`detail` 显示节点整体状态和摘要，`IO数据` 专门展示本次执行的端口级输入输出快照。

### 5.3 Config Tab 内容

**编辑模式**下显示可编辑表单，**流程模式**下以只读方式显示相同内容。

通用表单字段：
- 触发方式（如有 trigger-in 端口）：下拉选择
- 执行前延迟（ms）：数字输入
- 错误策略：chip toggle（stop / skip）
- 业务参数（引擎、模型、阈值等）：根据节点类型动态渲染

控件类型映射：

| 数据类型 | 控件 |
|---------|------|
| 枚举型选择（引擎、模型） | chip toggle 或 select dropdown |
| 字符串 | text input |
| 多行文本 | textarea |
| 数值 | number input 或 range slider |
| 布尔 | switch toggle |
| 字符串列表（如关键词） | tag input（可增删） |
| 字符串数组（如语言列表） | checkbox group |

### 5.4 Detail Tab 内容

```
┌──────────────────────────────────┐
│ ── 节点信息 ──                    │
│ 节点 ID: stt_listen_01           │
│ 节点类型: STT 持续监听            │
│ 行为模式: Listener（常驻监听）    │
│                                  │
│ ── 运行状态 ──                    │
│ ● 监听中                         │
│ 触发次数: 12                     │
│ 最近触发: 14:23:08               │
│ 最近关键词: "集合"                │
│                                  │
│ ── 端口列表 ──                    │
│ 输入:                            │
│   stt-in (audio) — 已连接        │
│   trigger-in (event) — 未连接    │
│ 输出:                            │
│   text-out (string) — 已连接     │
│   meta-keyword (string) — 隐藏   │
│   meta-confidence (number) — 隐藏│
└──────────────────────────────────┘
```

### 5.5 IO数据 Tab 内容（核心新增）

展示最近一次执行中各端口的实际输入/输出值：

```
┌──────────────────────────────────┐
│ ── 输入端口数据 ──                │
│                                  │
│ ▼ stt-in (audio)                 │
│   来源: AudioBus（内部音频总线）   │
│   状态: 持续接收                  │
│                                  │
│ ── 输出端口数据 ──                │
│                                  │
│ ▼ text-out (string)              │
│   "A点有敌人，注意"              │
│   类型: string                   │
│   产出时间: 14:23:05             │
│   → 流向: stt_history.hist-in   │
│                                  │
│ ▼ meta-keyword (string)          │
│   "集合"                         │
│   类型: string                   │
│   产出时间: 14:23:08             │
│   → 流向: condition.data-in-1   │
│                                  │
│ ▼ meta-confidence (number)       │
│   0.92                           │
│   类型: number                   │
│                                  │
│ 上次执行: 14:23:05 — 14:23:08    │
└──────────────────────────────────┘
```

### 5.6 Log Tab 内容

```
┌──────────────────────────────────┐
│ [14:23:05] 接收音频帧 #4521      │  ← muted
│ [14:23:05] 识别: "A点有敌人"     │  ← info
│ [14:23:06] 无关键词 → 继续监听   │  ← muted
│ [14:23:08] 识别: "需要集合"      │  ← info
│ [14:23:08] ★ 关键词匹配 → 触发   │  ← warn + highlight
│ [14:23:10] 触发下游: stt_history │  ← info
│ ── 新执行 14:30:00 ──            │  ← 分隔线
│ [14:30:01] 接收音频帧 #5001      │
│ ...                              │
│                         共 47 条 │
│                        [清空日志] │
└──────────────────────────────────┘
```

---

## 6. 流程走查：暗区竞标赛

### 6.1 完整流程拓扑

```
                              ┌─────────────────────┐
                              │   流程参数           │
                              │ skill_prompt: "你是  │
                              │ 暗区突围战术助手..." │
                              └─────────┬───────────┘
                                        │ (注入到 LLM context_build)
                                        ▼
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ ①        │    │ ②        │    │ ③            │    │ ④        │    │ ⑤        │    │ ⑥        │
│ 上传图片  │───→│ OCR 识别  │    │ STT 持续监听  │    │ LLM 生成  │───→│ TTS 合成  │───→│ TS 输出   │
│ input_   │    │ ocr      │    │ stt_listen   │    │ llm       │    │ tts       │    │ ts_output │
│ image    │    └──────────┘    └──────┬───────┘    └─────┬──────┘    └──────────┘    └──────────┘
└──────────┘                          │                  │
                                      │ stt-out          │ llm-in
                                      ▼                  ▲
                               ┌──────────────┐    ┌──────────────┐
                               │ ③b           │    │ ④a           │
                               │ STT History  │───→│ ContextBuild │
                               │ stt_history  │    │ context_build│
                               └──────────────┘    └──────────────┘
                                                      ▲        ▲
                                                      │        │
                                              ctx-in2 │        │ ctx-in1
                                                      │        │
                                              ┌───────┘        └───────┐
                                              │ OCR文本           skill_prompt
                                              │ (来自② ocr-out)   (来自流程参数)
```

### 6.2 执行时序

```
用户操作: 上传图片 → 激活流程

Step 0: 流程启动
  → stt_listen 自动进入 LISTENING 状态（常驻监听）
  → input_image 等待用户上传

Step 1: 用户上传图片
  → input_image: PENDING → PROCESSING → COMPLETED
  → 产出 img-out (image)
  → 触发 trigger-out (event)

Step 2: OCR 识别
  → ocr: PENDING → PROCESSING → COMPLETED
  → 产出 ocr-out (string: "地图: 北部山地区域...")
  → OCR 文本存入 accumulated_context

Step 3: STT 持续监听循环
  ┌─ 循环体 ─────────────────────────────┐
  │ stt_listen: LISTENING                │
  │   → 接收音频 → PROCESSING            │
  │   → 识别文本 "A点有敌人"             │
  │   → COMPLETED, 产出 text-out         │
  │                                      │
  │ stt_history: PENDING → PROCESSING    │
  │   → 累积到历史窗口                    │
  │   → 检查关键词: "敌人" 不在关键词列表 │
  │   → COMPLETED, condition_result:     │
  │     "skipped"                        │
  │   → 回到 stt_listen LISTENING ───────┘
  │
  │ ... 多轮循环后 ...
  │
  │ stt_listen: LISTENING
  │   → 识别 "需要集合"
  │   → COMPLETED, 产出 text-out
  │
  │ stt_history: PENDING → PROCESSING
  │   → 检查关键词: "集合" 匹配!
  │   → COMPLETED, condition_result:
  │     "matched"
  │   → hist-trigger 事件触发下游 ──────┐
  └─────────────────────────────────────┘
                                        │
Step 4: ContextBuild                     ▼
  → context_build: PENDING → PROCESSING
  → 收集: skill_prompt + OCR文本 + stt_history + 对话历史
  → 构建 messages 数组
  → COMPLETED, 产出 ctx-out (messages)
                                        │
Step 5: LLM 流式生成                     ▼
  → llm: PENDING → PROCESSING
  → 流式生成，每 chunk 推送到前端
  → COMPLETED, 产出 llm-out (string)
                                        │
Step 6: TTS 合成                         ▼
  → tts: PENDING → PROCESSING
  → 逐句合成为音频
  → COMPLETED, 产出 tts-out (audio, segments[])
                                        │
Step 7: TS 播放                          ▼
  → ts_output: PENDING → PROCESSING
  → 逐段发送到 TeamSpeak
  → COMPLETED, 播放完成
                                        │
Step 8: 自动回到 Step 3 继续监听         │
  → stt_listen 重新进入 LISTENING ───────┘
```

### 6.3 节点连接关系

```json
{
  "connections": [
    { "id": "c1", "from": "input_image.img-out",     "to": "ocr.ocr-in",         "type": "data" },
    { "id": "c2", "from": "input_image.trigger-out",  "to": "ocr.trigger-in",    "type": "event" },
    { "id": "c3", "from": "ocr.ocr-out",              "to": "context_build.ctx-in2", "type": "data" },
    { "id": "c4", "from": "stt_listen.text-out",      "to": "stt_history.hist-in","type": "data" },
    { "id": "c5", "from": "stt_history.hist-out",     "to": "context_build.ctx-in3","type": "data" },
    { "id": "c6", "from": "stt_history.hist-trigger", "to": "context_build.trigger-in","type": "event" },
    { "id": "c7", "from": "context_build.ctx-out",    "to": "llm.llm-in",        "type": "data" },
    { "id": "c8", "from": "llm.llm-out",              "to": "tts.tts-in",        "type": "data" },
    { "id": "c9", "from": "tts.tts-out",              "to": "ts_output.out-in",  "type": "data" }
  ]
}
```

> **注意**: stt_listen 到 context_build 的数据连线**不直接连**。stt_listen 的 text-out 连到 stt_history，stt_history 累积后产出 hist-out 再到 context_build。关键词触发通过 stt_history 的 hist-trigger (event) 控制 context_build 的执行时机。

---

## 7. 节点逐一设计

### 设计约定

每个节点设计包含以下维度：

| 维度 | 说明 |
|------|------|
| **基础信息** | type, 名称, icon, color, 宽度, 行为模式 |
| **端口定义** | 输入/输出端口，含 visibility、data_type、描述 |
| **Tab 定义** | 该节点有哪些 tab |
| **Flow Mode body** | 流程模式下节点卡片 body 区显示什么 |
| **Edit Mode body** | 编辑模式下各 tab 的 body 区显示什么 |
| **Config tab** | 可配置的参数及控件 |
| **Detail tab** | 节点详情显示内容 |
| **IO数据 tab** | 端口级输入输出数据快照 |
| **Log tab** | 日志内容特征 |
| **特殊交互** | 该节点独有的交互行为 |

---

### 7.1 input_image——上传图片

| 属性 | 值 |
|------|-----|
| type | `input_image` |
| 名称 | 上传图片 |
| icon | `upload_file` |
| color | secondary (#4edea3) |
| 宽度 | 220px |
| 行为模式 | Source（手动触发） |
| tabs | 无（整个 body 就是上传交互区） |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输出 | `img-out` | 图片数据 | image | always | 上传完成的图片 |
| 输出 | `trigger-out` | 触发信号 | event | always | 上传完成后通知下游 |

**Flow Mode body：**

```
┌──────────────────────────┐
│ 等待上传...              │  ← PENDING: 拖拽上传区
│ ┌──────────────────────┐ │
│ │   📤 点击或拖拽上传   │ │
│ └──────────────────────┘ │
│                          │
│ ── 或（已完成）──        │
│                          │
│ ✅ 已上传                │  ← COMPLETED
│ 📄 screenshot.png        │
│ 大小: 2.4 MB             │
│ 格式: PNG                │
│ ┌──────────────────────┐ │
│ │     [重新上传]        │ │
│ └──────────────────────┘ │
│                          │
│ ── 或（上传中）──        │
│                          │
│ 上传中... 45%            │  ← PROCESSING
│ ████████░░░░░░░░░       │
└──────────────────────────┘
```

**特殊交互**：
- 流程模式和编辑模式都支持文件上传（这是"使用"动作，不是"编辑"动作）
- 支持点击上传 + 拖拽上传
- 上传完成后自动触发下游 OCR（行为模式为 Source——手动触发）

---

### 7.2 ocr——OCR 识别

| 属性 | 值 |
|------|-----|
| type | `ocr` |
| 名称 | OCR 识别 |
| icon | `document_scanner` |
| color | secondary (#4edea3) |
| 宽度 | 220px |
| 行为模式 | Transform |
| tabs | config, detail, io-data, log |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `ocr-in` | 图片数据 | image | always | 来自 input_image 的图片 |
| 输入 | `trigger-in` | 触发 | event | on-demand | 显式触发信号 |
| 输出 | `ocr-out` | OCR 文本 | string | always | 识别出的文本 |
| 输出 | `done` | 完成 | event | on-demand | 识别完成事件 |
| 输出 | `meta-confidence` | 平均置信度 | number | on-demand | OCR 平均置信度 |
| 输出 | `meta-region-count` | 识别区域数 | number | on-demand | 识别到的文本区域数 |

**Flow Mode body：**

```
┌──────────────────────────┐
│ ● 状态: 待命             │  ← PENDING
│ 引擎: easyocr            │
│ 语言: 中文               │
│                          │
│ ── 或（处理中）──        │
│ ● 状态: 识别中           │  ← PROCESSING
│ 进度: 67%                │
│ ████████████░░░░░░░     │
│                          │
│ ── 或（已完成）──        │
│ ● 状态: 已完成           │  ← COMPLETED
│ 置信度: 0.87             │
│ "地图: 北部山地区域..."  │  ← 最近输出摘要（截断 60 字符）
│ 识别区域: 12 处          │
└──────────────────────────┘
```

**Config tab（编辑模式）：**

```
┌──────────────────────────┐
│ 引擎:                     │
│ [easyocr] [paddleocr]    │  ← chip toggle
│                          │
│ 识别语言:                 │
│ [✓] 中文  [✓] 英文       │  ← checkbox group
│ [ ] 日文  [ ] 韩文       │
│                          │
│ 置信度阈值:               │
│ [────────●────] 0.30     │  ← range slider
│                          │
│ ── 执行设置 ──            │
│ 触发方式: [信号到达 ▾]    │
│ 执行前延迟: [0] ms       │
│ 错误策略: [● 停止 ○ 跳过] │
└──────────────────────────┘
```

**IO数据 tab：**

```
┌──────────────────────────┐
│ ── 输入 ──               │
│ ocr-in (image)           │
│ 来源: input_image.img-out│
│ 文件: screenshot.png     │
│ 大小: 2.4 MB             │
│                          │
│ ── 输出 ──               │
│ ocr-out (string)         │
│ "地图: 北部山地区域..."  │
│ → context_build.ctx-in2  │
│                          │
│ meta-confidence (number) │
│ 0.87                     │
│                          │
│ meta-region-count (num)  │
│ 12                       │
└──────────────────────────┘
```

---

### 7.3 stt_listen——STT 持续监听

| 属性 | 值 |
|------|-----|
| type | `stt_listen` |
| 名称 | STT 持续监听 |
| icon | `mic_external_on` |
| color | primary (#adc7ff) |
| 宽度 | 320px |
| 行为模式 | Listener（常驻自触发，内部循环） |
| tabs | config, detail, io-data, log, fulltext |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `stt-in` | 音频帧 | audio | always | 来自 AudioBus（内部总线，画布不连线） |
| 输出 | `text-out` | 识别文本 | string | always | 每次识别的文本片段 |
| 输出 | `meta-keyword` | 触发关键词 | string | on-demand | 本次触发的关键词 |
| 输出 | `meta-confidence` | STT 置信度 | number | on-demand | 识别置信度 |
| 输出 | `meta-history-count` | 累积历史数 | number | on-demand | 当前累积的识别条数 |

> **注意**: stt_listen 监听器节点的 `text-out` 在每次识别时产出，可能多次。`meta-keyword` 仅在关键词匹配时产出。该节点自身不判断关键词（由 stt_history 或后端 AudioBus 处理）。

**Flow Mode body：**

```
┌──────────────────────────────┐
│ ● 状态: 监听中               │  ← LISTENING（蓝色脉冲）
│ 关键词: [求助] [集合] [撤退] │
│ 引擎: sensevoice             │
│ 采样率: 16000 Hz             │
│                              │
│ ── 实时识别 ──               │
│ "A点有敌人，注意"            │  ← 最近一次识别文本
│ "需要集合"                   │
│ "收到"                       │
│                              │
│ 累积: 47 条 | 触发: 12 次    │
│ 最后触发: 14:23:08 "集合"    │
│                              │
│ ── 或（处理中）──            │
│ ● 状态: 识别中               │  ← PROCESSING（短暂）
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░ 85%      │
└──────────────────────────────┘
```

**Config tab（编辑模式）:**

```
┌──────────────────────────────┐
│ 识别引擎:                     │
│ [sensevoice] [whisper]       │
│ [minimax]                    │
│                              │
│ 采样率: [16000] Hz           │
│                              │
│ 关键词列表:                   │
│ ┌──────────────────────────┐ │
│ │ [求助] [×]               │ │
│ │ [集合] [×]               │ │
│ │ [撤退] [×]               │ │
│ │ [+ 添加关键词]            │ │
│ └──────────────────────────┘ │
│                              │
│ ── 执行设置 ──               │
│ 触发方式: [常驻自触发]       │  ← 只读，Listener 固定
│ 错误策略: [● 停止 ○ 跳过]    │
└──────────────────────────────┘
```

**IO数据 tab（运行时）：**

```
┌──────────────────────────────┐
│ ── 输入 ──                   │
│ stt-in (audio)               │
│ 来源: AudioBus（内部总线）    │
│ 状态: 持续接收中              │
│ 当前缓冲: 3.2s               │
│                              │
│ ── 输出（最近一次） ──        │
│ text-out (string)            │
│ "需要集合"                   │
│ → stt_history.hist-in        │
│                              │
│ meta-keyword (string)        │
│ "集合"                       │
│                              │
│ meta-confidence (number)     │
│ 0.92                         │
│                              │
│ meta-history-count (number)  │
│ 47                           │
└──────────────────────────────┘
```

**Fulltext tab（运行时完整文本）：**

```
┌──────────────────────────────┐
│ [14:23:05] A点有敌人，注意    │
│ [14:23:06] 收到              │
│ [14:23:07] 我在B点           │
│ [14:23:08] 需要集合  ★触发   │
│ [14:23:12] 正在赶过去         │
│ [14:23:15] 注意后方          │
│ ...                          │
│                        47 条 │
└──────────────────────────────┘
```

---

### 7.4 stt_history——STT History·关键词判断

| 属性 | 值 |
|------|-----|
| type | `stt_history` |
| 名称 | STT History·关键词判断 |
| icon | `history_edu` |
| color | tertiary (#ffb695) |
| 宽度 | 280px |
| 行为模式 | Transform |
| tabs | config, detail, io-data, log |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `hist-in` | 文本片段 | string | always | 来自 stt_listen.text-out |
| 输入 | `trigger-in` | 触发 | event | on-demand | 显式触发信号 |
| 输出 | `hist-out` | STT 历史 | string_array | always | 累积的识别文本数组 |
| 输出 | `hist-trigger` | 关键词触发 | event | always | 关键词匹配时发出 |
| 输出 | `done` | 完成 | event | on-demand | 一般完成事件 |

**Flow Mode body：**

```
┌──────────────────────────────┐
│ ● 状态: 等待中               │  ← PENDING
│ 最大保留: 20 条              │
│                              │
│ ── 或（条件匹配-触发）──     │
│ ● 状态: 已完成               │  ← COMPLETED (matched)
│ ★ 关键词: "集合" 触发!       │
│ 历史: 47 条                  │
│ 最近: "A点有敌人"            │
│      "需要集合"  ★           │
│      "收到"                  │
│                              │
│ ── 或（条件不匹配-跳过）──   │
│ ● 状态: 已完成               │  ← COMPLETED (skipped)
│ 无关键词匹配                 │
│ 继续监听...                  │
└──────────────────────────────┘
```

**Config tab（编辑模式）：**

```
┌──────────────────────────────┐
│ 最大保留条数:                 │
│ [─────────────●────] 20      │  ← range slider (5-100)
│                              │
│ 上下文窗口:                   │
│ [128000] tokens              │
│                              │
│ ── 关键词设置 ──              │
│ （关键词列表继承自            │
│  stt_listen 的配置，         │
│  此处只读显示）               │
│ [求助] [集合] [撤退]         │
│                              │
│ ── 执行设置 ──               │
│ 触发方式: [数据就绪]          │
│ 错误策略: [● 停止 ○ 跳过]    │
└──────────────────────────────┘
```

**IO数据 tab：**

```
┌──────────────────────────────┐
│ ── 输入 ──                   │
│ hist-in (string)             │
│ 来源: stt_listen.text-out   │
│ 最近: "需要集合"             │
│                              │
│ ── 输出 ──                   │
│ hist-out (string_array)      │
│ ["A点有敌人", "收到",        │
│  "我在B点", "需要集合", ...] │
│ 共 47 条                     │
│ → context_build.ctx-in3      │
│                              │
│ hist-trigger (event)         │
│ ★ 已触发（关键词: "集合"）   │
│ → context_build.trigger-in   │
│                              │
│ 本次条件结果: matched        │
└──────────────────────────────┘
```

---

### 7.5 context_build——ContextBuild

| 属性 | 值 |
|------|-----|
| type | `context_build` |
| 名称 | ContextBuild |
| icon | `hub` |
| color | primary (#adc7ff) |
| 宽度 | 250px |
| 行为模式 | Transform |
| tabs | config, detail, io-data, log |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `ctx-in1` | Skill Prompt | string | always | 系统提示词 |
| 输入 | `ctx-in2` | OCR 文本 | string | always | 来自 OCR |
| 输入 | `ctx-in3` | STT 历史 | string_array | always | 来自 stt_history |
| 输入 | `ctx-in4` | 对话历史 | string_array | on-demand | 额外对话上下文 |
| 输入 | `trigger-in` | 触发 | event | always | 来自 stt_history.hist-trigger |
| 输出 | `ctx-out` | 组合上下文 | messages | always | LLM 格式的 messages 数组 |
| 输出 | `done` | 完成 | event | on-demand | 构建完成事件 |

**Flow Mode body：**

```
┌──────────────────────────────┐
│ ● 状态: 等待触发             │  ← PENDING
│ 已配置输入: 3 路             │
│                              │
│ ── 或（构建中）──            │
│ ● 状态: 构建上下文           │  ← PROCESSING
│ 已收集:                     │
│  ✓ OCR 文本 (486 tokens)    │
│  ✓ STT 历史 (47条, 2103 tk) │
│  ✓ Skill Prompt (62 tk)     │
│ 总 tokens: 2651 / 4096      │
│ ██████████░░░░░░ 65%       │
│                              │
│ ── 或（已完成）──            │
│ ● 状态: 已完成               │  ← COMPLETED
│ 消息数: 3                    │
│ 总 tokens: 2651              │
│ 触发下游: llm_01             │
└──────────────────────────────┘
```

**Config tab（编辑模式）：**

```
┌──────────────────────────────┐
│ ── 输入源配置 ──              │
│                              │
│ Skill Prompt:                 │
│ ┌──────────────────────────┐ │
│ │ 你是暗区突围的战术助手，  │ │
│ │ 请根据OCR地图信息和       │ │
│ │ 语音上下文生成战术指导... │ │
│ └──────────────────────────┘ │
│ 来源: [$flow.skill_prompt ▾] │ ← 可改为固定值/流程参数
│                              │
│ OCR 文本:                    │
│ 来源: [● 连线 ○ 参数 ○ 固定] │
│ 连线: ocr.ocr-out           │
│                              │
│ STT 历史:                    │
│ 来源: [● 连线 ○ 参数 ○ 固定] │
│ 连线: stt_history.hist-out  │
│                              │
│ ── 构建设置 ──               │
│ 最大上下文长度:               │
│ [4096] tokens                │
│                              │
│ ── 执行设置 ──               │
│ 触发方式: [信号到达]          │
│ 错误策略: [● 停止 ○ 跳过]    │
└──────────────────────────────┘
```

**IO数据 tab：**

```
┌──────────────────────────────┐
│ ── 输入 ──                   │
│ ctx-in1 (string)             │
│ 来源: 流程参数 skill_prompt  │
│ "你是暗区突围的战术助手..."  │
│                              │
│ ctx-in2 (string)             │
│ 来源: ocr.ocr-out           │
│ "地图: 北部山地区域..."      │
│                              │
│ ctx-in3 (string_array)       │
│ 来源: stt_history.hist-out  │
│ ["A点有敌人",..., "需要集合"]│
│ 共 47 条                     │
│                              │
│ ── 输出 ──                   │
│ ctx-out (messages)           │
│ [                            │
│   { role: "system",          │
│     content: "你是..." },    │
│   { role: "user",            │
│     content: "OCR: ...       │
│     语音记录: ..." }         │
│ ]                            │
│ → llm.llm-in                │
│                              │
│ 总 tokens: 2651              │
└──────────────────────────────┘
```

---

### 7.6 llm——LLM 生成

| 属性 | 值 |
|------|-----|
| type | `llm` |
| 名称 | LLM 生成 |
| icon | `smart_toy` |
| color | primary (#adc7ff) |
| 宽度 | 250px |
| 行为模式 | Transform |
| tabs | config, detail, io-data, log |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `llm-in` | 上下文 | messages | always | 来自 context_build |
| 输入 | `trigger-in` | 触发 | event | on-demand | 显式触发信号 |
| 输出 | `llm-out` | 生成文本 | string | always | 流式生成的完整文本 |
| 输出 | `done` | 完成 | event | on-demand | 生成完成事件 |
| 输出 | `meta-token-count` | Token 消耗 | number | on-demand | 消耗的 token 数 |
| 输出 | `meta-reasoning` | 思考过程 | string | on-demand | LLM reasoning 内容 |
| 输出 | `meta-model` | 模型名 | string | on-demand | 实际使用的模型 |

**Flow Mode body：**

```
┌──────────────────────────────┐
│ ● 状态: 等待上游             │  ← PENDING
│ 模型: gpt-4-turbo            │
│ Temperature: 0.7             │
│                              │
│ ── 或（生成中-流式）──      │
│ ● 状态: 生成中               │  ← PROCESSING（蓝色脉冲）
│ 模型: gpt-4-turbo            │
│ ██████████░░░░░░ 65%       │
│                              │
│ 流式输出:                    │
│ "根据OCR地图显示，你们当前    │
│  位于北部山区。我方侦察到     │
│  A点有两名敌人，建议..."     │
│  █ ← 流式光标                │
│                              │
│ ── 或（已完成）──            │
│ ● 状态: 已完成               │  ← COMPLETED
│ 消耗: 1,234 tokens           │
│ 回复: "根据OCR地图显示..."   │  ← 截断 80 字符
│ 含思考过程: 是               │
│ 触发下游: tts_01             │
└──────────────────────────────┘
```

**Config tab（编辑模式）：**

```
┌──────────────────────────────┐
│ 模型选择:                     │
│ [gpt-4-turbo] [gpt-4o]      │
│ [deepseek-v3] [自定义...]    │
│                              │
│ Temperature:                  │
│ [─────────●───] 0.70         │  ← range slider (0-2)
│                              │
│ Max Tokens:                   │
│ [2048]                       │
│                              │
│ 流式输出: [● 开启 ○ 关闭]    │  ← switch toggle
│                              │
│ ── 执行设置 ──               │
│ 触发方式: [数据就绪]          │
│ 错误策略: [● 停止 ○ 跳过]    │
└──────────────────────────────┘
```

**IO数据 tab：**

```
┌──────────────────────────────┐
│ ── 输入 ──                   │
│ llm-in (messages)            │
│ 来源: context_build.ctx-out  │
│ [                            │
│   { role: "system", ... },   │
│   { role: "user", ... }      │
│ ]                            │
│ 总 tokens: 2651              │
│                              │
│ ── 输出 ──                   │
│ llm-out (string)             │
│ "根据OCR地图显示，你们当前    │
│  位于北部山区。我方侦察到     │
│  A点有两名敌人，建议          │
│  从B点绕后包抄..."           │
│ → tts.tts-in                │
│                              │
│ meta-token-count (number)    │
│ 输入: 2651, 输出: 486        │
│ 总计: 3137                   │
│                              │
│ meta-reasoning (string)      │
│ "分析地图上的敌人分布..."    │
│                              │
│ meta-model (string)          │
│ gpt-4-turbo                  │
└──────────────────────────────┘
```

---

### 7.7 tts——TTS 合成

| 属性 | 值 |
|------|-----|
| type | `tts` |
| 名称 | TTS 合成 |
| icon | `record_voice_over` |
| color | outline (#8b90a0) |
| 宽度 | 220px |
| 行为模式 | Transform |
| tabs | config, detail, io-data, log |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `tts-in` | 文本 | string | always | 来自 LLM 的文本 |
| 输入 | `trigger-in` | 触发 | event | on-demand | 显式触发信号 |
| 输出 | `tts-out` | 合成音频 | audio | always | 合成的音频数据 |
| 输出 | `done` | 完成 | event | on-demand | 合成完成事件 |

**Flow Mode body：**

```
┌──────────────────────────┐
│ ● 状态: 等待上游          │  ← PENDING
│ 引擎: edge               │
│ 音色: YunxiNeural        │
│                          │
│ ── 或（合成中）──        │
│ ● 状态: 合成中            │  ← PROCESSING
│ 当前句: 2/8              │
│ ██████░░░░░░░░ 25%     │
│ "A点有两名敌人，"        │  ← 正在合成的句子
│                          │
│ ── 或（已完成）──        │
│ ● 状态: 已完成            │  ← COMPLETED
│ 共 8 句, 12.3s           │
│ 触发下游: ts_output_01   │
└──────────────────────────┘
```

**Config tab（编辑模式）：**

```
┌──────────────────────────┐
│ 合成引擎:                 │
│ [edge] [minimax]         │
│                          │
│ 音色:                    │
│ [YunxiNeural ▾]         │  ← select dropdown
│                          │
│ 语速:                    │
│ [────────●────] 1.0     │  ← range slider (0.5-2.0)
│                          │
│ ── 执行设置 ──           │
│ 触发方式: [数据就绪]      │
│ 错误策略: [● 停止 ○ 跳过] │
└──────────────────────────┘
```

**IO数据 tab：**

```
┌──────────────────────────┐
│ ── 输入 ──               │
│ tts-in (string)          │
│ 来源: llm.llm-out       │
│ "根据OCR地图显示..."     │
│ 文本长度: 486 字符        │
│                          │
│ ── 输出 ──               │
│ tts-out (audio)          │
│ 共 8 段音频              │
│ 总时长: 12.3s            │
│ → ts_output.out-in      │
│                          │
│ 分段详情:                │
│ 1. "根据OCR地图显示..."  │
│ 2. "我方侦察到A点..."   │
│ ...                      │
└──────────────────────────┘
```

---

### 7.8 ts_output——TS 音频输出

| 属性 | 值 |
|------|-----|
| type | `ts_output` |
| 名称 | TS 音频输出 |
| icon | `volume_up` |
| color | secondary (#4edea3) |
| 宽度 | 220px |
| 行为模式 | Sink |
| tabs | 无（整个 body 显示播放信息） |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输入 | `out-in` | 音频数据 | audio | always | 来自 TTS |
| 输入 | `trigger-in` | 触发 | event | on-demand | 显式触发信号 |
| 输出 | `out-done` | 播放完成 | event | always | 播放完成通知 |

**Flow Mode body：**

```
┌──────────────────────────┐
│ ● 状态: 等待音频          │  ← PENDING
│                          │
│ ── 或（播放中）──        │
│ ● 状态: 播放中            │  ← PROCESSING
│ 片段: 3/8                │
│ ████████░░░░░░ 38%     │
│ "我方侦察到A点..."       │  ← 当前播放片段
│                          │
│ ── 或（已完成）──        │
│ ● 状态: 播放完成          │  ← COMPLETED
│ 已播放: 8/8 段           │
│ 自动回到监听...          │
└──────────────────────────┘
```

**特殊交互**：
- Sink 节点，不产出业务数据
- `out-done` 事件通知流程该轮对话完成，可触发监听器回到 LISTENING
- 无 config tab（播放模式在流程模式下固定为 segment 逐句播放）

---

### 7.9 ts_input——TS 音频输入

| 属性 | 值 |
|------|-----|
| type | `ts_input` |
| 名称 | TS 音频输入 |
| icon | `headset_mic` |
| color | secondary (#4edea3) |
| 宽度 | 220px |
| 行为模式 | Source |
| tabs | 无 |

**端口定义：**

| 方向 | ID | label | data_type | visibility | 说明 |
|------|-----|-------|-----------|------------|------|
| 输出 | `audio-out` | 音频流 | audio | always | 发布到 AudioBus |
| 输出 | `trigger-out` | 触发信号 | event | always | 音频就绪通知 |

**Flow Mode body：**

```
┌──────────────────────────┐
│ ● 状态: 收集中            │  ← LISTENING
│ 缓冲: 3.2s / 10 MB      │
│ 采样率: 16000 Hz         │
│ 通道: 单声道             │
│                          │
│ 音频流发布到 AudioBus    │
│ → stt_listen 消费       │
└──────────────────────────┘
```

> **注意**：ts_input 不暴露 AudioBus 连线。AudioBus 是后端内部机制，前端画布只在 ts_input 和 stt_listen 的 detail 区显示"内部总线连接"字样即可。

---

## 8. 组件实现指南

### 8.1 需要新增/修改的前端文件

```
frontend/src/
  components/
    pipeline/
      nodes/
        InputImageNode.vue      ← 新增：上传图片节点 body
        OcrNode.vue             ← 新增：OCR 节点 body
        STTListenNode.vue       ← 新增：STT 监听节点 body
        STTHistoryNode.vue      ← 新增：STT 历史节点 body
        ContextBuildNode.vue    ← 新增：上下文构建节点 body
        LLMNode.vue             ← 新增：LLM 节点 body
        TTSNode.vue             ← 新增：TTS 节点 body
        TSOutputNode.vue        ← 新增：TS 输出节点 body
        TSInputNode.vue         ← 新增：TS 输入节点 body
        registry.js             ← 修改：填充组件注册表
      IOPort.vue                ← 修改：添加端口数据类型图标、点击弹窗触发
      NodeCard.vue              ← 修改：集成 body 组件、Flow/Edit 模式 body 切换
      PortPopover.vue           ← 新增：端口点击弹窗（只读/可编辑两种模式）
    panels/
      DynamicPanel.vue          ← 修改：添加 IO数据 tab，增强 tab 内容
      NodeConfigForm.vue        ← 新增：通用配置表单组件
```

### 8.2 NodeCard.vue 修改要点

```
当前 NodeCard.vue：
  - 已有 header、tab bar、端口渲染、状态边框
  - 缺失：body 区根据 type + status + activeTab 动态渲染

修改方案：
  1. 在 body 区引入 <component :is="nodeBodyComponent" v-bind="bodyProps" />
  2. bodyProps 根据 editMode / activeTab / nodeStatus 计算
  3. 编辑模式：activeTab 来自本地 ref（用户可切换）
  4. 流程模式：activeTab 锁定为 "detail"
  5. 无 tab 的节点（tabs=[]）：直接渲染 body 组件，不渲染 tab bar
```

### 8.3 IOPort.vue 修改要点

```
当前 IOPort.vue：
  - 已有拖拽连线、端口拖动、状态样式
  - 缺失：点击弹窗（端口配置 / 只读查看）

修改方案：
  1. 添加 @click.stop 事件 → emit('portClick', ...)
  2. 在 PipelineView 中监听 portClick → 打开 PortPopover
  3. PortPopover 内容根据 mode（flow=只读, edit=可配置）切换
  4. 端口添加 data-type 属性，事件端口显示菱形图标
```

### 8.4 PortPopover.vue 设计

```vue
<!-- PortPopover.vue -->
<template>
  <div class="port-popover" :style="popoverStyle">
    <!-- 只读模式（流程模式） -->
    <template v-if="readonly">
      <PortReadonlyView :port="port" :node="node" :runtime="runtime" />
    </template>

    <!-- 编辑模式 -->
    <template v-else>
      <PortEditView
        :port="port"
        :node="node"
        :connection="connection"
        @save="onSave"
        @disconnect="onDisconnect"
      />
    </template>
  </div>
</template>
```

### 8.5 节点 body 组件模板

以 `OcrNode.vue` 为例：

```vue
<template>
  <div class="ocr-node-body">
    <!-- 流程模式：固定显示 detail -->
    <template v-if="!editMode || activeTab === 'detail'">
      <NodeStatusDisplay :status="status" :summary="summary" />
      <NodeOutputPreview :data="data" :config="config" />
    </template>

    <!-- 编辑模式 + config tab -->
    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="config" :fields="configFields" @update="onUpdate" />
    </template>

    <!-- IO数据 tab -->
    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :node="node" :runtime="runtime" />
    </template>

    <!-- Log tab -->
    <template v-if="activeTab === 'log'">
      <NodeLogView :logs="logs" :nodeId="node.id" />
    </template>
  </div>
</template>
```

### 8.6 NodeConfigForm.vue——通用配置表单

一个数据驱动的表单组件，根据字段定义自动渲染正确控件：

```ts
interface ConfigField {
  key: string              // 配置键名
  label: string            // 显示标签
  type: 'select' | 'text' | 'textarea' | 'number' | 'switch' | 'range' | 'tags' | 'checkbox-group' | 'chip-toggle'
  options?: { value: string, label: string }[]  // select/chip-toggle 选项
  min?: number             // range 最小值
  max?: number             // range 最大值
  step?: number            // range 步进
  placeholder?: string
  description?: string     // 字段说明
  disabled?: boolean       // 是否禁用
}
```

---

## 附录 A：各节点 Tab 汇总

| 节点 | tabs | body 组件 |
|------|------|-----------|
| `input_image` | 无 | InputImageNode |
| `ocr` | config, detail, io-data, log | OcrNode |
| `ts_input` | 无（可选 detail, io-data） | TSInputNode |
| `stt_listen` | config, detail, io-data, log, fulltext | STTListenNode |
| `stt_history` | config, detail, io-data, log | STTHistoryNode |
| `context_build` | config, detail, io-data, log | ContextBuildNode |
| `llm` | config, detail, io-data, log | LLMNode |
| `tts` | config, detail, io-data, log | TTSNode |
| `ts_output` | 无（可选 detail, io-data） | TSOutputNode |

## 附录 B：端口可见性速查（流程模式）

| 节点 | 始终可见的端口（always + 有数据来源） |
|------|-------------------------------------|
| `input_image` | img-out, trigger-out |
| `ocr` | ocr-in (有连线), ocr-out |
| `stt_listen` | text-out, stt-in (AudioBus) |
| `stt_history` | hist-in, hist-out, hist-trigger |
| `context_build` | ctx-in1, ctx-in2, ctx-in3, trigger-in, ctx-out |
| `llm` | llm-in, llm-out |
| `tts` | tts-in, tts-out |
| `ts_output` | out-in, out-done |

## 附录 C：与现有代码的兼容路径

1. **不改 NodeCard 壳结构**——header、tab bar、端口渲染保持现有实现
2. **body 区用插槽注入**——NodeCard 增加 `<component :is>` 替代默认 body，现有默认 body 作为 fallback
3. **IOPort 增加点击 emit**——现有 `portClick` 事件已定义，只需在 PipelineView 中监听并弹出 PortPopover
4. **DynamicPanel 增加 IO数据 tab**——在现有 tab 数组中增加 `{ id: 'io-data', label: 'IO数据' }`
5. **tab 切换逻辑**——流程模式下 `activeTab` 计算属性返回 `'detail'` 强制锁定
6. **registry.js 逐步填充**——先从 OcrNode 和 STTListenNode 开始，后续迭代补充其余节点
