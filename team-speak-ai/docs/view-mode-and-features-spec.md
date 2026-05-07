# 视图模式与功能规格

> 定义各视图模式下 UI 显示/隐藏规则、流程参数设计、系统变量设计、节点日志缓存，以及对应实现计划。
> 本规格与 [node-system-design.md](./node-system-design.md)、[architecture-spec.md](./architecture-spec.md)、[pipeline-editor-spec.md](./pipeline-editor-spec.md) 互补。

---

## 目录

1. [模式系统概述](#1-模式系统概述)
2. [视图模式矩阵](#2-视图模式矩阵)
3. [各区域显示/隐藏规则](#3-各区域显示隐藏规则)
4. [流程参数设计](#4-流程参数设计)
5. [系统变量设计](#5-系统变量设计)
6. [节点日志缓存设计](#6-节点日志缓存设计)
7. [端口可见性规则](#7-端口可见性规则)
8. [实现计划与差距分析](#8-实现计划与差距分析)

---

## 1. 模式系统概述

### 1.1 两个模式 + 一个执行条件

前端画布的状态由两个模式决定，pipeline 执行状态是一个附加条件（不是第三种视图）：

```
交互模式  ─── 流程模式（使用流程） / 编辑模式（设计流程结构）
视图滤镜  ─── 全视图 / 数据流视图 / 事件流视图

pipeline 状态：空闲 / 运行中（不是独立的视图模式，只是流程模式下的执行状态）
```

> **待命中、处理中、已完成、失败**这些是节点的运行时状态，同样不是独立视图。它们是流程模式下节点根据自身状态展示的不同内容。

### 1.2 核心逻辑：流程模式 vs 编辑模式

**流程模式是使用模式，编辑模式是设计模式。**

```
流程模式（默认）                 编辑模式（按需进入）
─────────────────────         ─────────────────────
使用这个流程                   设计这个流程的结构
· 上传图片（input_image）       · 拖入新节点
· 运行管线                     · 创建/删除连线
· 查看节点状态/详情/日志        · 修改节点配置（引擎、参数等）
· 查看端口数据来源（只读）      · 露出 on-demand 端口
· 查看流程参数                  · 新建/修改/删除流程参数
· 切换视图滤镜                  · 撤销/重做
                               · 拖拽移动节点
                               · 删除节点
```

**关键区分**：
- **流程模式也能做、编辑模式也能做的**：查看日志、查看详情、查看端口、切换视图
- **只有流程模式能做的**：运行管线、以及节点自身的手动操作（如 input_image 上传文件——这是使用流程的一部分，不是编辑结构）
- **只有编辑模式能做的**：增删节点、连线、改配置、撤销重做

**为什么 input_image 特殊？** 因为上传文件是"使用"动作——用户在使用这个流程时，需要手动上传一张图片来触发 OCR。这是运行时交互，不是设计流程结构。OCR、LLM、TTS 等节点没有手动操作，数据到达自动处理，所以流程模式下只需可读查看。

| 维度 | 控制什么 |
|------|---------|
| **交互模式** (流程/编辑) | 能否修改流程**结构**（节点、连线、配置）。对运行时操作（上传、运行、查看）没有限制 |
| **视图滤镜** (全/数据/事件) | 哪些端口和连线可见。纯显示滤镜，不影响任何操作权限 |
| **pipeline 状态** (空闲/运行中) | 运行中强制切换到流程模式；节点状态实时更新；已连线端口显示数据流动画 |

### 1.3 模式切换

| 切换 | 触发方式 | 说明 |
|------|---------|------|
| 流程 → 编辑 | 点击顶栏 `[流程设置]` | 进入结构设计模式，可增删节点/连线/改配置 |
| 编辑 → 流程 | 点击顶栏 `[流程模式]` | 返回使用模式，自动保存未持久化的编辑 |
| 视图切换 | 画布底部 `[全部]/[数据流]/[事件流]` | 纯显示滤镜，不改变交互模式 |
| 运行 | 顶栏 `[运行]` 或 `pipeline.run` 命令 | 强制切换到流程模式 |
| 运行结束 | 后端 `pipeline.completed` 事件 | 保持流程模式 |

---

## 2. 视图模式矩阵

### 2.1 有效组合（2 模式 × 3 视图 = 6 种）

```
                   全视图          数据流视图       事件流视图
                   ──────          ────────         ────────
流程模式           ✓ (默认)         ✓                ✓
编辑模式           ✓               ✓                ✓
```

> pipeline 运行中时，强制锁定为**流程模式**。编辑模式不可用。

---

## 3. 各区域显示/隐藏规则

> 下表中的"流程+Idle"和"流程+Running"是**同一流程模式下**的两种 pipeline 状态（空闲 vs 执行中），不是两种不同的视图模式。列出来是为了方便对照 pipeline 运行前后 UI 的差异。

### 3.1 区域总览

```
┌──────────────────────────────────────────────────────────────────┐
│ ① Top Nav Bar                                             56px   │
├────────┬─────────────────────────────────────────┬────────────────┤
│②Sidebar│            ③ Canvas                     │④ Right Panel   │
│256px   │                                         │ 320px          │
│        │  ┌─────────┐    ┌─────────┐            │ (条件显示)     │
│        │  │ Node A  │───→│ Node B  │            │                │
│        │  └─────────┘    └─────────┘            │                │
│        │      ⑤ Node Palette (悬浮)              │                │
│        │                                        │                │
│        │  ⑥ Canvas Controls [全部|数据|事件] [-]│                │
├────────┴─────────────────────────────────────────┴────────────────┤
│ ⑦ Bottom Status Bar                                         32px │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 ① Top Nav Bar（顶栏）

| 元素 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| Logo + 标题 | ✓ | ✓ | ✓ |
| 流程名称 | ✓ | ✓ | ✓ |
| `[运行]` 按钮 (primary) | ✓ | ✗ | ✗ |
| `[流程设置]` 按钮 (ghost) | ✓ | ✗ | ✗ |
| `[流程模式]` 按钮 (ghost) | ✗ | ✗ | ✓ |
| 保存状态指示器 | ✗ | ✗ | ✓ |
| `[撤销]` 按钮 | ✗ | ✗ | ✓ (canUndo 时启用) |
| `[重做]` 按钮 | ✗ | ✗ | ✓ (canRedo 时启用) |
| 通知铃铛 | ✓ | ✓ | ✓ |
| 运行中状态标签 | ✗ | ✓ "运行中" (蓝色脉冲) | ✗ |

> **`[运行]` 按钮**：流程模式下的主操作入口（primary-btn），点击触发 `pipeline.run`。**`[流程设置]`** 是 ghost-btn，点击进入编辑模式修改流程结构。

### 3.3 ② Sidebar（侧栏）

**所有模式下均显示**，内容不变。

| 属性 | 所有模式 |
|------|---------|
| 可见性 | ✓ 始终显示 |
| 交互 | ✓ 始终可点击（切换流程、展开折叠） |
| 流程树右键菜单 (⋮) | ✓ 始终可用 |

> 侧栏的流程管理操作（新建、重命名、删除、导出/导入）不受画布模式影响——它们操作的是流程文件，与当前画布处于查看还是编辑无关。

### 3.4 ③ Canvas（画布）

| 属性 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 网格背景 | ✓ | ✓ | ✓ |
| 平移（鼠标中键） | ✓ | ✓ | ✓ |
| 缩放（滚轮/Ctrl+滚轮） | ✓ | ✓ | ✓ |
| 画布尺寸（overflow scroll） | ✓ | ✓ | ✓ |
| 空白区域右键菜单 | ✗ | ✗ | ✓ "画布设置" |

**视图滤镜影响：**

| 属性 | Full View | Data View | Event View |
|------|----------|----------|-----------|
| 数据连线 + 数据端口 | ✓ 显示 | ✓ 显示 | ✗ 隐藏 |
| 事件连线 + 事件端口 | ✓ 显示 | ✗ 隐藏 | ✓ 显示 |
| 推导事件边（虚线） | ✓ 显示 | ✗ 隐藏 | ✓ 显示 |

### 3.5 ④ NodeCard（节点卡片）

| 属性 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 节点可见 | ✓ | ✓ | ✓ |
| 单击选中 | ✓ | ✓ | ✓ |
| 双击打开右侧面板 | ✓ (只读) | ✓ (只读) | ✓ (可编辑) |
| 节点拖拽移动 | ✗ | ✗ | ✓ |
| 右键菜单 | ✗ | ✗ | ✓ |
| Delete 删除 | ✗ | ✗ | ✓ |
| 步骤号徽章 (①②③) | ✓ | ✓ | ✓ |
| Tab 栏 | ✓ (不可切换，固定 detail) | ✓ (不可切换) | ✓ (可切换) |
| 状态边框颜色 | ✓ (默认灰色) | ✓ (实时状态色) | ✓ (默认灰色) |
| 状态点动画 | ✗ | ✓ (processing/listening) | ✗ |
| 进度条 | ✗ | ✓ (processing 时) | ✗ |
| 关键词脉冲点 | ✗ | ✓ (listening + 关键词命中时) | ✗ |
| 节点 body (detail 区) | 静态内容 | **实时更新** | 静态内容 |
| 选中高亮边框 | ✓ (白色) | ✓ (白色) | ✓ (蓝色发光) |
| 文件上传交互 (input_image) | ✓ | ✓ | ✓ |

> **流程模式下双击节点**：打开右侧面板，所有 tab 只读。**编辑模式下双击节点**：打开右侧面板，配置 tab 可编辑。

### 3.6 ⑤ IOPort（端口圆点）

#### 3.6.1 可见性规则

端口可见性由**三个条件同时决定**：

```
端口可见 = (端口有数据来源 OR 当前为 Edit Mode) AND (视图滤镜允许此端口类型) AND (端口 visibility=always OR 用户已手动露出)
```

**"有数据来源"** 指端口满足以下任一条件：
- 有连线（上游数据/下游消费）
- 配置了固定值
- 引用了流程参数（`$param.xxx`）或流程变量（`$flow.xxx`）
- 有模板预设默认值

核心规则：
- **流程模式**：只显示"活"的端口（有数据来源的）。无连线、无配置、无默认值的"死"端口隐藏。
- **编辑模式**：全部端口可见（供用户配置和连线）。

| 模式 | 端口可见规则 |
|------|------------|
| **流程 + Idle** | 有数据来源的端口可见。可点击查看（只读弹窗），不可编辑。 |
| **流程 + Running** | 同 流程+Idle，已连线端口额外显示数据流动画（`flowing` 蓝色脉冲）。可点击查看。 |
| **编辑 + Idle** | **全部端口可见**（always 端口始终显示，on-demand 端口通过 "+" 露出）。可拖拽连线、点击配置。 |

> **"死"端口**：无连线、无固定值、无参数引用、无预设默认值的端口——流程模式下隐藏，编辑模式下显示供用户配置。

#### 3.6.2 视图滤镜对端口的影响

| 端口 data_type | Full View | Data View | Event View |
|---------------|----------|----------|-----------|
| `image`, `audio`, `string`, `string_array`, `messages`, `any`, `number`, `list`, `dict` | ✓ | ✓ | ✗ |
| `event` | ✓ | ✗ | ✓ |

#### 3.6.3 端口交互可用性

| 交互 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 悬停高亮 + label tooltip | ✓ | ✓ | ✓ |
| 点击端口 → 查看弹窗（只读） | ✓ | ✓ | — |
| 点击输入端口 → 配置弹窗（可编辑） | ✗ | ✗ | ✓ |
| 点击输出端口 → 下游查看弹窗 | ✗ | ✗ | ✓ |
| 从输出端口拖拽连线 | ✗ | ✗ | ✓ |
| 端口手动拖动调整位置 | ✗ | ✗ | ✓ |
| 端口 "+" 按钮（露出 on-demand 端口） | ✗ | ✗ | ✓ |
| 数据流动画 (flowing) | ✗ | ✓ | ✗ |

**流程模式下的端口查看弹窗**（只读）：

```
┌────────────────────────────┐
│ 端口: ctx-in-stt           │
│ 类型: string               │
│                            │
│ 数据来源: 连线              │
│ 上游: stt_listen.text-out  │
│                            │
│ [关闭]                     │  ← 无编辑选项
└────────────────────────────┘
```

> **关于 "+" 按钮**：仅在 Edit Mode + 节点 selected/hovered 时显示在端口区域旁。点击展示可选 on-demand 端口菜单（§7）。

#### 3.6.4 端口视觉状态（Flow + Running）

| 状态 | 边框颜色 | 背景 | 动画 |
|------|---------|------|------|
| 未连接 | `#8b90a0` (outline-variant) | `#10131b` | 无 |
| 已连接，无数据流 | `#4edea3` (secondary) | `rgba(78,222,163,0.12)` | 无 |
| 数据流通中 | `#4a8eff` (primary-container) | `rgba(74,142,255,0.18)` | `portFlowPulse` 蓝色呼吸 |
| 事件触发 | `#ffb695` (tertiary) | `rgba(255,182,149,0.18)` | 单次脉冲闪烁 |

### 3.7 ⑥ Connections（连线）

#### 3.7.1 可见性规则

连线可见性由**视图滤镜**决定：

| 连线 type | Full View | Data View | Event View |
|----------|----------|----------|-----------|
| `data` | ✓ 实线蓝色 | ✓ 实线蓝色 | ✗ 隐藏 |
| `event` | ✓ 虚线橙色 | ✗ 隐藏 | ✓ 虚线橙色 |
| 推导事件边 | ✓ 虚线(淡) | ✗ 隐藏 | ✓ 虚线(淡) |

#### 3.7.2 连线交互可用性

| 交互 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 悬停高亮 | ✗ | ✓ | ✓ |
| 单击选中 | ✗ | ✗ | ✓ |
| 选中 + Delete 删除 | ✗ | ✗ | ✓ |
| 右键删除菜单 | ✗ | ✗ | ✓ |
| 数据流动画 | ✗ | ✓ (processing 时) | ✗ |

#### 3.7.3 连线视觉状态（Flow + Running）

| 状态 | 颜色 | 线型 | 动画 |
|------|------|------|------|
| 静态（无数据流） | `#4edea3` (data) / `#adc7ff` (event) | 虚线(data) / 实线(event) | 无 |
| 活跃数据流 | `#4a8eff` | 实线 + 发光 | `flowDash` 虚线流动动画 |
| 事件触发瞬间 | `#ffb695` | 实线 | 单次高亮脉冲 |

### 3.8 ⑤ NodePalette（悬浮工具面板）

| 属性 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 可见性 | ✗ | ✗ | ✓ |
| 拖拽节点到画布 | ✗ | ✗ | ✓ |
| 折叠/展开 | ✗ | ✗ | ✓ |

**面板内容**（Edit Mode 下）：

```
┌──────────────────────┐
│ 工具面板        [−]  │
├──────────────────────┤
│ ── 输入 ──           │
│ ▌📤 上传图片         │
│ ▌🎤 TS 音频输入      │
│ ── 处理 ──           │
│ ▌📄 OCR 识别         │
│ ▌🔗 ContextBuild     │
│ ▌🤖 LLM 生成         │
│ ── 音频 ──           │
│ ▌🎙 STT 监听         │
│ ▌📋 STT History      │
│ ── 控制 ──           │  ← 新增分类
│ ▌🔀 条件分支         │
│ ▌🔗 多路聚合         │
│ ▌⏱ 延迟等待         │
│ ▌🔔 通知推送         │
│ ── 输出 ──           │
│ ▌🔊 TTS 合成         │
│ ▌📢 TS 音频输出      │
│ ── 子流程 ──         │  ← 新增分类
│ ▌📦 节点组           │
│ ▌🔄 循环             │
│ ── 系统 ──           │  ← 新增分类
│ ▌⚙ 系统变量          │
└──────────────────────┘
```

> 新增节点类型（condition, merge, delay, notify, break, group, loop, sys_var）参见 [node-system-design.md](./node-system-design.md) §2 和 §9。

### 3.9 ④ Right Panel（右侧详情面板）

| 属性 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 面板可见 | ✓ (节点选中时) | ✓ (节点选中时) | ✓ (节点选中时) |
| 打开方式 | 双击节点 / 单击选中节点 | 双击节点 / 单击选中节点 | 双击节点 / 单击选中节点 |
| 关闭方式 | 点击 ✕ / 点击画布空白 / Escape | ← 同 | ← 同 |
| Config tab | ✓ **只读** | ✓ 只读 | ✓ **可编辑** |
| Detail tab | ✓ 只读 | ✓ 只读（实时更新 I/O） | ✓ 只读 |
| Log tab | ✓ 只读（显示缓存日志） | ✓ 只读（实时追加） | ✓ 只读 |
| Fulltext tab | ✓ 只读 | ✓ 只读（实时追加） | ✓ 只读 |

> **关键区别**：流程模式下右侧面板所有 tab 只读，编辑模式下 Config tab 可编辑。Detail/Log/Fulltext 在任何模式下都是只读。

### 3.10 ⑥ Canvas Controls（画布控制栏）

**所有模式下均显示**，固定在画布左下角。

```
[全部] [数据流] [事件流]  |  [-] [100%] [+] [适应]
```

| 元素 | 流程 + Idle | 流程 + Running | 编辑 + Idle |
|------|------------|---------------|-------------|
| 视图切换按钮 | ✓ | ✓ | ✓ |
| 缩放按钮 | ✓ | ✓ | ✓ |
| 适应画布按钮 | ✓ | ✓ | ✓ |

### 3.11 ⑦ Bottom Status Bar（底部状态栏）

**所有模式下均显示**。

| 元素 | 所有模式 |
|------|---------|
| TeamSpeakBot 状态 | ✓ |
| Backend 状态 | ✓ |
| Pipeline 状态 | ✓ |
| API / 文档 / 支持 链接 | ✓ |

Pipeline 状态文本随执行状态变化：

| 执行状态 | Pipeline 状态显示 |
|---------|-----------------|
| Idle | "编辑中" (Edit Mode) / "就绪" (Flow Mode) |
| Running | "运行中" (蓝色脉冲) |

---

## 4. 流程参数设计

### 4.1 两层概念区分

| 概念 | 是什么 | 在哪编辑 | 举例 |
|------|--------|---------|------|
| **流程设置** (Flow Settings) | 流程自身的元数据 | 侧栏右键菜单 / 顶栏 `[画布设置]` | 名称、图标、画布尺寸、skill_prompt |
| **流程参数** (Flow Parameters) | 流程级自定义变量，供节点引用 | Edit Mode 下的小弹窗 | `game_mode = "competitive"`, `threshold = 0.7` |

> 本节聚焦**流程参数**（自定义 key-value 变量）。流程设置（名称、画布等）沿用现有机制，通过侧栏 ⋮ 菜单和顶栏 `[画布设置]` 编辑。

### 4.2 流程参数定义

流程参数是用户自定义的 key-value 对，存储在 Flow JSON 的 `params` 字段中。节点配置中可通过 `$param.参数名` 引用。

```json
{
  "id": "darkzone_championship",
  "name": "暗区锦标赛",
  "params": {
    "game_mode": "competitive",
    "trigger_keyword": "集合",
    "stt_threshold": 0.7,
    "max_response_tokens": 2048
  },
  "nodes": [ ... ],
  "connections": [ ... ]
}
```

| 属性 | 说明 |
|------|------|
| key | 参数名（string，唯一，snake_case） |
| value | 参数值（string / number / boolean / array / object） |
| 引用方式 | 在节点端口配置中引用 `$param.key_name` |

### 4.3 使用场景

流程参数在节点配置中被引用，作为端口的数据来源之一。详见 [node-system-design.md](./node-system-design.md) §5.2 解析链：

```
引擎解析链（优先级从高到低）：
  1. 端口有连线 → 取上游数据
  2. 端口引用流程参数 → $param.xxx
  3. 端口引用流程变量 → $flow.xxx
  4. 端口有固定值 → 手动填写的值
  5. 模板预设默认值
```

**示例**：LLM 节点的 `max_tokens` 不写死，而是引用流程参数：

```
llm 节点 → temperature 端口配置：
  数据来源: 流程参数 → $param.stt_threshold
```

修改流程参数 `stt_threshold` 的值，所有引用它的节点自动生效。

### 4.4 前端入口与交互

**入口**：流程模式和编辑模式下均可点击打开，顶栏或画布区域有一个 `[流程参数]` 入口。

**流程模式**：弹窗**只读**，显示当前参数列表，不可修改。
**编辑模式**：弹窗**可编辑**，支持新建/修改/删除参数。

**点击后弹出小窗口**（Popover，非右侧大面板）：

```
┌─────────────────────────────────────┐
│ 流程参数                       [✕]  │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────┬────────────────┐  │
│  │ 参数名        │ 值              │  │
│  ├──────────────┼────────────────┤  │
│  │ game_mode    │ competitive    │  │  ← 点击行可编辑
│  │ trigger_key..│ 集合            │  │
│  │ stt_threshold│ 0.7            │  │
│  │ max_respons..│ 2048           │  │
│  └──────────────┴────────────────┘  │
│                                     │
│  [+ 新建参数]                        │  ← 点击新增一行
│                                     │
├─────────────────────────────────────┤
│              [完成]                  │
└─────────────────────────────────────┘
```

**交互细节**：

| 操作 | 行为 |
|------|------|
| **新建** | 点击 `[+ 新建参数]` → 表格新增空行 → 输入 key 和 value |
| **修改** | 点击已有行 → 进入编辑态 → 修改 key 或 value |
| **删除** | 行右侧 ⋮ 菜单 → "删除" / 或行尾 × 按钮 |
| **保存** | 每次增/改/删即时通过 `flow.update` 命令持久化 |
| **类型** | value 自动推断类型（数字→number, true/false→boolean, 其他→string） |
| **验证** | key 不能为空、不能重复、仅允许 `[a-z0-9_]` |

### 4.5 后端存储

流程参数作为 Flow JSON 的 `params` 字段持久化：

```
backend/data/flows/darkzone_championship.json
  {
    ...
    "params": { "game_mode": "competitive", ... }
  }
```

`flow.update` 命令支持 partial update 流程 JSON 的任意顶层字段（包括 `params`）。

### 4.6 与流程设置的区别

| | 流程设置 (Flow Settings) | 流程参数 (Flow Parameters) |
|------|--------------------------|---------------------------|
| **内容** | name, icon, group, canvas, skill_prompt, enabled | 用户自定义 key-value |
| **编辑方式** | 侧栏 ⋮ 菜单 / 创建流程对话框 / 顶栏画布设置 | Edit Mode 下的 Popover 小弹窗 |
| **引用方式** | 不被节点引用（skill_prompt 除外，自动注入 LLM） | 节点通过 `$param.xxx` 引用 |
| **存储** | Flow JSON 顶层字段 | Flow JSON 的 `params` 字段 |

---

## 5. 系统变量设计

### 5.1 概述

系统变量是**跨流程共享的全局配置**，通过专用的 `sys_var` 节点读写。与流程变量（`$flow.*`，单次执行内有效）不同，系统变量持久化到磁盘，服务重启后恢复。

详见 [node-system-design.md](./node-system-design.md) §8.3–8.5。

### 5.2 sys_var 节点类型定义

```python
# 后端 NodeRegistry 注册
@NodeRegistry.register("sys_var")
class SysVarNode(BaseNode):
    """系统变量读写节点 — Transform 行为模式"""

    type_def = NodeTypeDef(
        type="sys_var",
        name="系统变量",
        icon="settings",
        color="outline",
        default_config={
            "mode": "read",        # "read" | "write" | "update"
            "var_name": "",
            "default_value": "",
        },
        tabs=[
            TabDef(id="config", label="配置"),
            TabDef(id="detail", label="详情"),
            TabDef(id="log", label="日志"),
        ],
        ports=PortsDef(
            inputs=[
                PortDef(id="data-in", label="写入值", data_type="any",
                        visibility="on-demand",
                        position=PortPosition(side="left", order=0)),
                PortDef(id="trigger-in", label="触发", data_type="event",
                        visibility="always",
                        position=PortPosition(side="left", order=1)),
            ],
            outputs=[
                PortDef(id="data-out", label="读取值", data_type="any",
                        visibility="always",
                        position=PortPosition(side="right", order=0)),
                PortDef(id="done", label="完成", data_type="event",
                        visibility="always",
                        position=PortPosition(side="right", order=1)),
            ],
        ),
    )
```

### 5.3 三种操作模式

| 模式 | 触发后行为 | data-in | data-out | done 事件 |
|------|-----------|---------|----------|----------|
| **read** | 读取系统变量值 | 不使用 | 变量值（或默认值） | ✓ |
| **write** | 覆盖写入系统变量 | 要写入的值 | 不产出 | ✓ |
| **update** | 合并更新（dict 场景） | 要合并的值 | 不产出 | ✓ |

### 5.4 系统变量持久化

```
backend/data/system_vars.json

{
  "llm_model": "gpt-4-turbo",
  "tts_voice": "zh-CN-YunxiNeural",
  "stt_engine": "sensevoice",
  "keyword_list": ["求助", "集合", "撤退"]
}
```

- 写入时自动持久化
- 服务启动时加载到内存
- 支持嵌套 key（如 `ocr.defaults.language` → `{"ocr": {"defaults": {"language": "zh"}}}`）

### 5.5 新增 WebSocket 命令

| action | dir | params | 说明 |
|--------|-----|--------|------|
| `sys_var.list` | C→S | `{}` | 查询所有系统变量 |
| `sys_var.list_result` | S→C | `{variables: {key: value, ...}}` | 返回全部系统变量 |
| `sys_var.get` | C→S | `{var_name}` | 查询单个系统变量 |
| `sys_var.get_result` | S→C | `{var_name, value}` | 返回单个变量值 |
| `sys_var.set` | C→S | `{var_name, value}` | 设置系统变量（手动，不走节点） |
| `sys_var.set_result` | S→C | `{var_name, value}` | 确认设置 |

### 5.6 前端 SysVarNode.vue 组件

**Config tab**：

```
┌──────────────────────────────────────┐
│  ⚙ 系统变量                          │
├──────────────────────────────────────┤
│  操作模式: [read ▾]                   │
│  变量名:   [llm_model_____________]  │
│  默认值:   [gpt-4-turbo___________]  │  ← 仅 read 模式显示
└──────────────────────────────────────┘
```

**Detail tab**（运行时）：

| 模式 | 显示内容 |
|------|---------|
| read | 当前读取的值（只读展示） |
| write | "已写入: xxx → llm_model" |
| update | "已更新: {key: val} → llm_model" |

### 5.7 系统设置面板（前端独立页面）

除了通过 `sys_var` 节点在流程中读写，前端还应提供一个**系统设置面板**来直接管理常用系统变量。入口在侧栏「系统设置」分区：

```
侧栏 → 系统设置 → LLM设置 → 面板显示:
  ┌──────────────────────────────────────┐
  │  LLM 设置                            │
  │                                      │
  │  默认模型  [gpt-4-turbo ▾]           │
  │  Temperature  [0.7 ────●──] 0.7     │
  │  Max Tokens   [____2048____]         │
  │                                      │
  │  这些设置作为系统变量存储，可被       │
  │  sys_var 节点在流程中读取/覆盖。      │
  └──────────────────────────────────────┘
```

系统设置面板通过 `sys_var.list` / `sys_var.set` 命令与后端通信，不经过 PipelineEngine。

---

## 6. 节点日志缓存设计

### 6.1 当前状态

- 每个节点在执行期间通过 `node.log_entry` 接收实时日志
- 日志存储在**前端内存**（`execution.js` store，每节点上限 200 条 FIFO）
- **问题**：执行完成后日志被丢弃——用户想回看"刚才发生了什么"时数据已经没了

### 6.2 需求

> "每一个节点都缓存数据" — 执行完成后日志不丢弃，保留在前端内存中作为小缓存，方便用户回看。

### 6.3 设计：前端内存缓存

**不做后端持久化**。日志是前端的内存缓存，仅在当前会话存活：

```
execution.js store:
  nodeLogs: {
    "stt_listen_01": [
      { ts: "14:23:05", level: "info", message: "识别: \"A点有敌人\"" },
      { ts: "14:23:08", level: "warn", message: "★ 关键词匹配 → 触发!" },
      ...共 200 条
    ],
    "llm_01": [ ... ],
    ...
  }
```

| 维度 | 策略 |
|------|------|
| 存储位置 | 前端 `execution.js` Pinia store |
| 每节点上限 | 200 条（FIFO，超出移除最旧） |
| 生命周期 | 页面刷新后清空（会话级缓存） |
| 执行完成 | **不清空**，缓存保留供回看 |
| 新一次执行 | 追加到已有缓存（同一节点合并，超出上限移除最旧） |
| 节点删除 | 对应缓存删除 |
| 切换流程 | 缓存保留（下次切回时仍在） |
| 手动清空 | Log Tab 底部 "清空日志" 按钮 |

> **为什么不做后端持久化**：日志量大（每次执行数百条），持久化成本高但使用频率低。前端会话缓存已覆盖核心场景（执行完回看）。如需持久化作为后续迭代。

### 6.4 节点标签页分工

节点上的数据展示分为两个独立标签页：

| 标签页 | 内容 | 说明 |
|--------|------|------|
| **详情 (Detail)** | 本节点的输入/输出数据快照 | 最近一次执行时各端口实际收到的输入值、产出的输出值 |
| **日志 (Log)** | 本节点的执行日志条目 | 专门的小标签页，仅显示 `node.log_entry` 推送的日志 |

### 6.5 Detail Tab：输入输出数据

```
┌──────────────────────────────────────┐
│ [配置] [详情] [日志]                 │
├──────────────────────────────────────┤
│ ── 输入 ──                           │
│ ctx-in-stt  (string)                 │
│ "A点有敌人，注意"                    │
│                                      │
│ ctx-in-ocr  (string)                 │
│ (无数据)                             │
│                                      │
│ ── 输出 ──                           │
│ msg-out  (messages)                  │
│ [{"role":"user","content":"..."}]    │
│                                      │
│ 上次执行: 14:23:05                   │
└──────────────────────────────────────┘
```

每条输入/输出显示：端口名、数据类型、实际值（长文本截断）。每次执行后自动更新。

### 6.6 Log Tab：专门的小标签页

```
┌──────────────────────────────────────┐
│ [配置] [详情] [日志]                 │
├──────────────────────────────────────┤
│ [14:23:05] 接收上下文 (tokens: 486)  │  ← info
│ [14:23:06] 构建完成，消息数: 3       │  ← success
│ [14:23:08] 触发下游: llm_01          │  ← info
│ [14:23:10] 执行完成                  │  ← success
│ ...                                  │
│                        共 45 条 ────│
│                        [清空日志]    │
└──────────────────────────────────────┘
```

**交互**：
- 新日志到达时，若用户在日志 tab 且滚动在底部 → 自动滚动
- 若用户已向上滚动 → 不自动滚动，显示 "↓ 新日志" 提示
- 默认展示最新 50 条，向上滚动查看更早
- "清空日志" 按钮清除该节点日志缓存
- 日志条目按 `level` 着色（同 `node.log_entry` 规范）

### 6.7 日志缓存 vs 实时推送

| 阶段 | Detail Tab | Log Tab |
|------|-----------|---------|
| **执行中** | `node.status_changed` → 实时更新输入输出数据 | `node.log_entry` → 实时追加日志，自动滚动 |
| **执行完成** | 保留最后一次执行的数据快照 | 缓存保留，显示静态历史日志 |
| **新一次执行** | 输入输出数据刷新 | 插入分隔线后继续追加 |

```
[14:23:08] ★ 关键词匹配 → 触发!       ← 上次执行
[14:23:10] 触发下游: context_build
── 新执行 14:30:00 ──────────────────  ← 自动分隔线
[14:30:01] 接收上下文 (tokens: 512)   ← 当前执行
[14:30:02] 构建完成，消息数: 4
```

---

## 7. 端口可见性规则

### 7.1 always / on-demand 端口

来自 [node-system-design.md](./node-system-design.md) §3.1：

| 标记 | 含义 | Flow Mode 行为 | Edit Mode 行为 |
|------|------|---------------|---------------|
| **always** | 核心端口 | 有数据来源时显示（连线/固定值/参数/默认值） | 始终显示 |
| **on-demand** | 扩展端口 | 有数据来源时显示 | 默认隐藏，通过 "+" 露出 |

> **"有数据来源"** = 端口满足以下任一：有连线 / 配置了固定值 / 引用了流程参数或变量 / 有模板预设默认值。无任何数据来源的"死"端口在流程模式下隐藏。

### 7.2 "+" 按钮交互

**仅在 Edit Mode + 节点 hovered/selected 时显示**：

```
端口区域底部出现:
  [+ 添加端口]  ← 点击展开菜单

菜单内容（按分组）:
  ┌────────────────────────┐
  │ 数据端口               │
  │ + ctx-in-ocr           │
  │ + ctx-in-stt           │
  │ ─────────────          │
  │ 诊断端口               │
  │ + meta-keyword         │
  │ + meta-confidence      │
  │ ─────────────          │
  │ 事件端口               │
  │ + trigger-in           │
  │ + done                 │
  └────────────────────────┘
```

- 勾选 → 端口出现在节点上（可连线、可单独配置）
- 取消勾选 → 端口隐藏（已有连线自动断开）
- 菜单外点击或 Escape 关闭

### 7.3 各节点端口分类总览

| 节点类型 | always 端口 | on-demand 端口 | repeatable 端口组 |
|---------|------------|---------------|------------------|
| `input_image` | img-out, trigger-out | — | — |
| `ts_input` | audio-out, done | — | — |
| `ocr` | img-in, text-out | trigger-in, done | — |
| `stt` | audio-in, text-out | trigger-in, done | — |
| `stt_listen` | text-out, done | meta-keyword, meta-confidence, meta-history-count | — |
| `stt_history` | hist-in, hist-out, hist-trigger | trigger-in, done | — |
| `context_build` | ctx-in-1, msg-out | ctx-in-2..6, trigger-in, done | ctx-in (max 6) |
| `llm` | msg-in, text-out | trigger-in, done, meta-token-count, meta-reasoning, meta-model | — |
| `tts` | text-in, audio-out | trigger-in, done | — |
| `ts_output` | audio-in, done | trigger-in | — |
| `condition` | trigger-in, data-in-1, true | data-in-2..4, false, data-out-1..4 | data-in (max 4), data-out (max 4) |
| `filter` | trigger-in, data-in-1, pass | data-in-2..4, reject, data-out-1..4 | data-in (max 4), data-out (max 4) |
| `merge` | data-out, done | trigger-in, data-in (repeatable) | data-in (max 8) |
| `delay` | trigger-in, done | data-in, data-out | — |
| `break` | trigger-in, break-out | — | — |
| `notify` | trigger-in, done | data-in | — |
| `group` | trigger-in, data-in, data-out, done | — | — |
| `loop` | trigger-in, data-in, data-out, done | break-in, iter | — |
| `sys_var` | trigger-in, data-out, done | data-in | — |

### 7.4 未连接端口的视觉提示（Edit Mode）

| 端口状态 | 视觉提示 |
|---------|---------|
| always 输入端口未连接 | 端口圆点灰色 + 悬停显示 "未连接" tooltip |
| always 输出端口未连接 | 端口圆点灰色（正常——不是所有输出都需要下游） |
| on-demand 端口未连接 | 同 always |
| 推荐连接（如 ocr 的 img-in）未连接 | 端口圆点 + 黄色警告边框（`#ffb695`） |

---

## 8. 实现计划与差距分析

### 8.1 当前代码 vs 目标设计差距

#### 8.1.1 视图模式相关

| 差距 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| 端口 view mode 过滤 | 仅连线 SVG 有 `data-only`/`event-only` CSS 类，端口圆点无 | IOPort 组件接收 data_type，应用对应 CSS 类 | P0 |
| Flow Mode 下未连线端口隐藏 | Flow Mode 下端口全部隐藏 | Flow Mode 下仅已连线端口可见，未连线端口（被丢弃的）隐藏 | P0 |
| 选中节点高亮边框 | NodeCard 有 `selected` class | 已有，确认在 Edit Mode 下正常工作 | — |
| Canvas Controls 常驻 | 已有 | 保持现状 | — |

#### 8.1.2 流程参数

| 差距 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| 流程参数 `params` 字段 | Flow JSON 无 `params` 字段 | Flow JSON 新增 `params: {}` 存储自定义 key-value | P1 |
| 流程参数编辑弹窗 | 不存在 | Edit Mode 下的 Popover 小弹窗，支持新建/修改/删除参数 | P1 |
| 端口引用 `$param.xxx` | 不存在 | 端口配置弹窗的数据来源选项中增加"流程参数" | P2 |
| 引擎解析链支持 | 不存在 | 引擎按优先级解析：连线 → $param → $flow → 固定值 → 预设 | P2 |

#### 8.1.3 系统变量

| 差距 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| `sys_var` 节点类型 | 不存在 | 后端注册 + 前端 SysVarNode.vue | P1 |
| 系统变量持久化 | 不存在 | `data/system_vars.json`，启动加载，写入时自动存盘 | P1 |
| `sys_var.*` WebSocket 命令 | 不存在 | 新增 `sys_var.list/get/set` 命令 | P1 |
| 系统设置面板 | 侧栏有入口但无实现 | 每个设置项对应面板，读写系统变量 | P2 |
| 流程变量 `$flow.*` | 不存在 | 引擎在节点产出后写入，端口配置引用 | P2 |

#### 8.1.4 节点日志缓存

| 差距 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| 日志缓存保留 | 执行完成后日志缓冲区被丢弃 | 执行完成后保留，仅页面刷新时清空（会话级缓存） | P1 |
| 多次执行日志合并 | 新执行覆盖旧日志 | 新执行日志追加到已有缓存，以分隔线区分 | P1 |
| 手动清空日志 | 不存在 | Log Tab 底部 "清空日志" 按钮 | P2 |
| 日志分隔线 | 不存在 | 新一次执行时自动插入分隔线 | P2 |

#### 8.1.5 新节点类型

| 节点类型 | 后端 | 前端 | 优先级 |
|---------|------|------|--------|
| `condition` | 需实现 | 需 ConditionNode.vue | P1 |
| `filter` (condition 预设) | 复用 condition | 同 ConditionNode.vue，预设配置 | P1 |
| `merge` | 需实现 | 需 MergeNode.vue | P1 |
| `delay` | 需实现 | 需 DelayNode.vue + 所有节点执行前延迟修饰 | P2 |
| `break` | 需实现 | 需 BreakNode.vue | P2 |
| `notify` | 需实现 | 需 NotifyNode.vue | P2 |
| `group` (子流程) | 需实现 | 需 GroupNode.vue + 子画布编辑器 | P2 |
| `loop` | 需实现 | 需 LoopNode.vue + 子画布编辑器 | P2 |
| `sys_var` | 需实现 | 需 SysVarNode.vue | P1 |
| `stt` (独立 STT) | 需实现 | 需 STTNode.vue | P2 |

### 8.2 分阶段实施建议

#### 阶段 1：视图模式完善（当前优先）

1. **端口 view mode 过滤** — IOPort.vue 添加 `data-only`/`event-only` CSS 类
2. **Flow Mode 端口规则** — 仅已连线端口可见，未连线端口隐藏
3. **右键画布菜单** — "流程设置" + "新建节点" 等快捷操作

#### 阶段 2：流程参数 + 系统变量 + 核心逻辑节点

1. **流程参数弹窗** — FlowParamsPopover.vue，新建/修改/删除自定义参数
2. **流程参数存储** — Flow JSON 新增 `params` 字段 + `flow.update` 命令
3. **`sys_var` 节点** — 后端节点类 + 前端组件 + 持久化
4. **`sys_var.*` WS 命令** — 查询/设置系统变量
5. **`condition` / `filter` / `merge` 节点** — 核心逻辑节点引擎 + 前端组件
6. **端口配置弹窗** — IOPort 点击弹出数据来源配置（连线/变量/固定值/流程参数）

#### 阶段 3：日志缓存 + 高级节点

1. **日志会话缓存** — execution.js 保留执行完成后的日志，多次执行合并
2. **Log Tab 增强** — 执行分隔线 + "清空日志" 按钮
3. **`delay` 修饰** — 所有节点执行前延迟
4. **`notify` / `break` 节点** — 通知推送 + 循环中断

#### 阶段 4：子流程 + 流程变量

1. **`group` / `loop` 节点** — 子画布编辑器 + 执行引擎
2. **流程变量 `$flow.*`** — 引擎在节点产出后自动写入，端口引用读取
3. **系统设置面板** — 侧栏系统设置各项的独立设置面板

### 8.3 需要新增/修改的文件清单

#### 后端新增

```
backend/
  core/
    nodes/
      condition_node.py       # 条件分支节点
      merge_node.py            # 多路聚合节点
      delay_node.py            # 延迟节点
      break_node.py            # 循环中断节点
      notify_node.py           # 通知推送节点
      sys_var_node.py          # 系统变量节点
    flow/
      log_manager.py           # 日志持久化管理
    config/
      system_vars.py           # 系统变量管理
  data/
    system_vars.json           # 系统变量持久化文件
    logs/                      # 日志目录
```

#### 后端修改

```
backend/
  core/
    pipeline/
      registry.py              # 注册新节点类型 + 扩展 PortDef (visibility, group, repeatable)
      definition.py            # 扩展 PortDef 数据类 (visibility, group, repeatable, min, max, multi)
    nodes/
      __init__.py              # 导入新节点模块
  api/
    routes/
      ws_main.py               # 新增 flow.update, sys_var.*, log.* handler
```

#### 前端新增

```
frontend/src/
  components/
    pipeline/
      nodes/
        ConditionNode.vue      # 条件分支节点组件
        MergeNode.vue          # 多路聚合节点组件
        DelayNode.vue          # 延迟节点组件
        BreakNode.vue          # 循环中断节点组件
        NotifyNode.vue         # 通知推送节点组件
        SysVarNode.vue         # 系统变量节点组件
        GroupNode.vue          # 子流程组节点组件
        LoopNode.vue           # 循环节点组件
    panels/
      FlowSettingsPanel.vue    # 流程设置面板
      PortConfigPopover.vue    # 端口配置弹窗
      SystemSettingsPanel.vue  # 系统设置面板
```

#### 前端修改

```
frontend/src/
  components/
    pipeline/
      IOPort.vue               # 添加 data-only/event-only CSS 类，添加 "+" 按钮
      NodeCard.vue              # 添加 on-demand 端口露出交互，meta 端口分组
      NodePalette.vue           # 新增节点分类（控制、子流程、系统）
      PipelineView.vue          # Flow+Running 下端口可见但不交互
      CanvasControls.vue        # 保持现状
    layout/
      AppLayout.vue             # 顶栏流程设置按钮改为打开 FlowSettingsPanel
      SidebarTreeNode.vue       # 系统设置项链接到对应设置面板
  stores/
    editor.js                   # 新增 flowMeta 更新方法，流程参数编辑
    execution.js                # 新增日志恢复逻辑
  api/
    pipeline.js                 # 新增 log.query, sys_var.* 命令
```

---

## 附录 A：模式 × 区域 速查表

| 区域 | 流程+Idle | 流程+Running | 编辑+Idle |
|------|----------|-------------|----------|
| **Top Nav** | Logo + 名称 + `[运行]` + `[流程设置]` + 铃铛 | Logo + 名称 + 运行标签 + 铃铛 | Logo + 名称 + `[流程模式]` + 保存状态 + `[撤销]` + `[重做]` + 铃铛 |
| **Sidebar** | ✓ 全功能 | ✓ 全功能 | ✓ 全功能 |
| **Canvas** | ✓ 平移/缩放 | ✓ 平移/缩放 | ✓ 平移/缩放 + 右键菜单 |
| **NodeCard** | 可选中/双击(只读面板)/上传交互 | 实时状态动画 + 可选中/双击(只读面板) | 可拖拽/双击(可编辑面板)/右键/删除 |
| **Ports** | 有数据来源的端口可见，可点击查看（只读弹窗） | 有数据来源的端口可见 + 数据流动画，可点击查看 | 全部端口可见，可连线/配置/拖动 |
| **Connections** | 静态显示，不可交互 | 数据流动画，不可交互 | 可选中/删除 |
| **NodePalette** | ✗ | ✗ | ✓ |
| **Right Panel** | ✓ 只读（节点选中时） | ✓ 只读（节点选中时，实时更新） | ✓ 可编辑 Config（节点选中时） |
| **Canvas Controls** | ✓ | ✓ | ✓ |
| **Bottom Bar** | ✓ | ✓ | ✓ |

## 附录 B：视图滤镜 × 连接/端口 速查表

| 元素 | Full View | Data View | Event View |
|------|----------|----------|-----------|
| data 类型连线 | ✓ 实线蓝色 | ✓ 实线蓝色 | ✗ |
| event 类型连线 | ✓ 虚线橙色 | ✗ | ✓ 虚线橙色 |
| 推导事件边 | ✓ 虚线(淡) | ✗ | ✓ 虚线(淡) |
| data 类型端口 (image/audio/string/...) | ✓ | ✓ | ✗ |
| event 类型端口 | ✓ | ✗ | ✓ |
