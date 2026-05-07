# 节点系统设计思想

> 版本: 2.1.0 | 更新: 2026-05-07

---

## 目录

1. [设计原则](#1-设计原则)
2. [节点分类体系](#2-节点分类体系)
3. [节点骨架：固定端口 + 按需可见](#3-节点骨架固定端口--按需可见)
4. [数据流与事件流：同一张图的两层语义](#4-数据流与事件流同一张图的两层语义)
5. [输入来源：解析链，非三选一](#5-输入来源解析链非三选一)
6. [透传与端口配对](#6-透传与端口配对)
7. [中间数据输出：meta-* 诊断端口](#7-中间数据输出meta--诊断端口)
8. [变量系统：流程变量与系统变量](#8-变量系统流程变量与系统变量)
9. [逻辑组件设计](#9-逻辑组件设计)
10. [子流程设计](#10-子流程设计)
11. [数据类型与兼容性](#11-数据类型与兼容性)
12. [执行时机与错误传播](#12-执行时机与错误传播)
13. [配置分层](#13-配置分层)
14. [撤销/重做机制](#14-撤销重做机制)
15. [运行时状态映射](#15-运行时状态映射)
16. [设计总结](#16-设计总结)
17. [迁移附录](#17-迁移附录)

---

## 1. 设计原则

### 核心理念

**节点 = 加工单元。** 接收东西，做处理，产出东西。节点卡片 = 通用壳 + 类型内容注入。壳负责端口渲染、标签页、动画、拖拽；内容由类型定义注入。

### 六大原则

| 原则 | 说明 |
|------|------|
| **壳与内容分离** | 节点卡片是通用容器，类型定义注入端口、标签页、配置面板 |
| **端口是类型契约** | 端口 ID 属于类型定义，实例可调行为（可见性、位置），不可改 ID |
| **数据流与事件流是同一张图的两层语义** | 不是两套连线系统。数据连线天然隐含事件关系。视图是滤镜，不改数据只改可见性 |
| **输入来源是解析链** | 引擎按优先级解析：连线数据 → 固定配置值 → 节点属性。不是用户选择的三选一 |
| **逻辑节点控制路径，不产生业务数据** | 逻辑节点的产出是控制信号（event），不是业务数据 |
| **预设是配置模板** | 预设和运行时无关，选预设 = 复制一份到实例配置，用户在此基础上改 |

---

## 2. 节点分类体系

按**运行时行为模式**分类：

```
节点类型（按行为模式）
│
├── Source（数据源）── 主动产出数据，自身是数据起点
│   ├── ts_input        TeamSpeak 音频输入（常驻，发布到 AudioBus）
│   └── input_image     图片上传（手动触发，产出 image）
│
├── Transform（数据转换）── 接收数据，处理后产出新数据
│   ├── ocr             图片 → 文本
│   ├── stt             音频 → 文本
│   ├── context_build   多源文本 → LLM messages
│   ├── llm             messages → 文本（流式）
│   ├── tts             文本 → 音频
│   ├── stt_history     累积 STT 文本 + 关键词判断（维护历史窗口）
│   └── sys_var         系统变量读写（读取/写入/更新全局配置）
│
├── Listener（常驻监听）── 后台持续运行，内部循环，条件满足时触发下游
│   └── stt_listen      订阅 AudioBus → STT → 关键词检测 → 触发下游
│
├── Logic（流程控制）── 不转换数据，控制执行路径和数据路由
│   ├── condition       条件分支（if/else）；filter 是其预设简化形态
│   ├── merge           多路聚合（wait_all / wait_any）
│   ├── delay           延迟等待
│   ├── break           循环中断（仅用于 loop 内部）
│   ├── notify          通知推送
│   └── loop            循环（子流程的特殊形态）
│
└── Sink（数据出口）── 消费数据，对外输出
    └── ts_output       TeamSpeak 音频播放
```

### 关键区分

| 行为模式 | 特点 | 例子 |
|----------|------|------|
| **Source** | 无上游数据连线，自身是数据起点 | ts_input, input_image |
| **Transform** | 数据进 → 处理后 → 数据出，纯函数式 | ocr, llm, tts |
| **Listener** | Source 的特殊形式，常驻后台，内部自循环 | stt_listen |
| **Logic** | 不修改数据内容，控制"往哪走""何时走" | condition, filter, merge |
| **Sink** | 消费数据，不产出供下游使用的业务数据 | ts_output |

---

## 3. 节点骨架：固定端口 + 按需可见

### 3.1 端口策略

**每个节点类型的端口全集是固定的**，但并非所有端口都需要展示。端口分为两类：

| 标记 | 含义 | 行为 |
|------|------|------|
| **always** | 核心端口 | **始终展示**，不可隐藏 |
| **on-demand** | 扩展端口 | **默认隐藏**，用户通过 "+" 按钮露出 |

> 命名说明：这里用 `always` / `on-demand` 而非 `required` / `optional`，因为 `required` 容易被误解为"必须有数据才能执行"——而可见性和数据就绪是两件独立的事。

用户的工作是**连线 + 按需露出端口**，不是"添加/创建"端口。

### 3.2 端口定义

```
PortDef:
  id: string              # "ctx-in-ocr"
  label: string           # "OCR 文本"
  data_type: string       # "string" | "audio" | "event" | ...
  visibility: "always" | "on-demand"
  group: string | null    # 所属端口组（repeatable 时共用）
  repeatable: boolean     # 是否允许多实例
  min: int | null         # 最少实例数
  max: int | null         # 最多实例数
  multi: boolean          # 是否允许多条连线连入/连出
  position:               # 渲染位置
    side: "left" | "right"
    order: int
```

### 3.3 端口组的可重复实例

部分节点需要同类型端口的多个实例（如 merge 的 N 个输入）。这不是"动态添加任意端口"，而是**同一端口定义的多个实例**。

适用的端口组：

| 节点 | 端口组 | min | max | 说明 |
|------|--------|-----|-----|------|
| `merge` | `data-in` | 1 | 8 | 聚合多路输入 |
| `context_build` | `ctx-in` | 1 | 6 | 多数据源上下文 |
| `condition` | `data-in` / `data-out` | 1 | 4 | 多路透传配对 |

**前端交互**：
- 节点拖入时展示 `min` 个实例
- 端口旁 "+" 按钮（当前 < max 时显示），点击新增一个实例
- 右键实例 → "移除"（当前 > min 时可用）
- 实例自动编号：`data-in-1`, `data-in-2`, ...

### 3.4 各节点类型的 always/on-demand 划分

```
ocr:
  always: img-in, text-out
  on-demand: trigger-in, done

context_build:
  always: ctx-in-1, msg-out
  on-demand: ctx-in-2, ctx-in-3, ctx-in-4, trigger-in, done

condition:
  always: data-in-1, trigger-in, true
  on-demand: data-out-1, false

merge:
  always: data-out, done
  on-demand: data-in (repeatable), trigger-in

stt_listen:
  always: text-out
  on-demand: done, meta-keyword, meta-confidence, meta-history-count
```

### 3.5 未连接端口的行为

- **always 输入端口未连接**：数据为空，节点仍执行（前端显示警告图标）
- **on-demand 端口未展示**：等同于不存在
- **on-demand 端口已展示但未连接**：数据为空/默认值
- **输出端口未连接**：产出被丢弃

---

## 4. 数据流与事件流：同一张图的两层语义

### 4.1 核心思想

**数据流和事件流不是两套连线系统，而是同一张有向图上的两层语义。**

- 数据视图回答："什么东西从哪到哪"
- 事件视图回答："谁什么时候会动"

一条从 A 的 `text-out` 到 B 的 `text-in` 的连线，**同时**表达了：
- 数据层：A 产出的文本流向 B
- 事件层：A 完成 → B 可以开始（隐含的触发关系）

不需要用户创建两条线。事件关系从数据连线中**推导**出来，在事件视图下**显式渲染**。

### 4.2 连线模型

```
ConnectionDef {
  id: string
  from_node: string
  from_port: string
  to_node: string
  to_port: string
  type: "data" | "event"     // 用于前端视图分组 + 引擎执行推导
}
```

`type` 字段的语义：

| type | 含义 | 前端渲染 | 引擎行为 |
|------|------|---------|---------|
| **data** | 数据连线（默认） | 数据视图显示，event 视图隐藏 | 传递数据 + **推导**事件关系 |
| **event** | 纯事件连线 | 事件视图显示，data 视图隐藏 | 只传递触发信号，不传数据 |

> **与当前代码的关系**：代码中 `ConnectionDef.type` 已有 `"data" | "event" | "trigger"` 三值。v2.1 去掉 `"trigger"`——触发关系由 data 连线推导或 event 连线显式表达，不需要第三种类型。迁移时 `"trigger"` 映射为 `"event"`。

### 4.3 三个视图：同一张图的三层滤镜

| 视图 | 滤掉 | 留下 | 看什么 |
|------|------|------|--------|
| **全视图** | 无 | 所有端口 + 所有连线 | 全局结构 |
| **数据视图** | event 端口 + 纯事件连线 | data 端口 + data 连线 | 数据怎么流转 |
| **事件视图** | data 端口 + 纯数据连线 | event 端口 + event 连线 + 数据连线衍生的事件边 | 谁触发谁 |

**全视图 = 数据视图 + 事件视图的并集。** 视图切换不改变节点位置、不改变端口存在与否，只改可见性。

### 4.4 数据连线隐含事件关系

```
示例：

数据视图下：
  [stt_listen]──text-out────(string)──→text-in [context_build]

事件视图下（同一张图，换滤镜）：
  [stt_listen]──done (推导)──(event)──→trigger (推导) [context_build]
```

用户画了一条从 `text-out` 到 `text-in` 的数据连线。引擎推导出：stt_listen 产出数据后，context_build 可以被触发。在事件视图下，这条**推导的事件边**被渲染为虚线，帮助用户理解执行顺序。

### 4.5 纯事件连线：当触发不伴随数据

当触发关系**无法从数据连线推导**时（两个节点之间没有数据依赖），用户手动创建纯事件连线：

```
场景：stt_listen 检测到关键词 → 发送通知

  [stt_listen]──done──(event)──→trigger-in [notify]

notify 不需要 stt_listen 的数据，消息内容来自自己的配置。
这是一条用户手动创建的纯事件连线（从 event 端口到 event 端口）。
```

**纯事件连线的创建方式**：用户从节点的 event 端口（done/true/false/pass 等）拖线到目标节点的 event 端口（trigger-in）。

### 4.6 事件扇出

一个事件同时触发多个下游，各下游数据来源独立：

```
                       ┌─→ trigger-in [context_build]
                       │   (context_build 的 text-in 连到 stt_listen.text-out)
  [stt_listen]──done ──┤
                       ├─→ trigger-in [notify]
                       │   (notify 的消息来自配置模板)
                       │
                       └─→ trigger-in [ocr]
                           (ocr 的 img-in 连到 input_image.img-out)
```

三个节点被同一个事件触发，各自从不同的数据源取数据。

### 4.7 前端视觉规范

| | 数据视图 | 事件视图 |
|------|---------|----------|
| **数据连线** | 实线，蓝色 (#adc7ff)，标签显示数据类型 | 实线（淡化），标签显示触发条件 |
| **事件连线** | 隐藏 | 虚线，橙色 (#ffb695)，标签显示事件名 |
| **推导事件边** | 隐藏 | 虚线（更淡），自动生成，表示隐含触发 |
| **event 端口** | 隐藏 | 显示（菱形图标） |
| **data 端口** | 显示（圆形图标） | 显示（淡化，仅当参与事件推导时） |

---

## 5. 输入来源：连线即默认，点击端口可覆盖

### 5.1 核心思想

**连线的存在本身就是配置。** 用户拖了线 → 数据从上游来，这是默认行为，不需要额外配置。

用户**只有**在需要覆盖默认行为时，才点击端口进行配置（改用流程变量、写死固定值等）。

### 5.2 引擎解析链

每个数据输入端口，引擎按以下优先级解析：

```
优先级 1: 端口有连线 → 取上游输出端口的数据（默认行为，无需任何配置）
优先级 2: 端口无连线，但用户手动配置了来源 →
            - 流程变量引用（$flow.xxx）
            - 固定值（手动填写的文本/数字）
            - 节点属性
优先级 3: 端口无连线、无手动配置，但节点类型的模板预设中有默认参数 → 取预设默认值
优先级 4: 都没有 → 该端口不参与本次执行，视为不存在（不阻止节点执行）
```

### 5.3 用户操作流程

```
正常情况（80% 场景）：
  拖线连接 → 完成。不需要打开任何配置面板。

需要覆盖时（点击端口）：
  点击 IO 端口 → 弹出端口配置弹窗 →
    ┌────────────────────────────┐
    │  端口: ctx-in-stt          │
    │                            │
    │  数据来源:                  │
    │  [● 连线] ← 当前状态       │
    │  [  流程变量]  ← 已连线时禁用│
    │  [  固定值]     ← 已连线时禁用│
    │  [  节点属性]   ← 已连线时禁用│
    │                            │
    │  （端口已连线时，来源切换    │
    │   被锁定。需先断开连线才    │
    │   能切换到其他来源）        │
    └────────────────────────────┘

无连线无配置（默认状态）：
  端口展示时检查模板预设 → 有默认值则使用 → 无默认值则不参与执行
```

### 5.4 模板预设中的默认参数

节点类型可以在 `default_config` 中为端口预设默认值。这样当端口未连线、用户也未手动配置时，端口仍有一个合理的初始值。

```
context_build 的 default_config:
  port_defaults:
    ctx-in-1: "你是一个 TeamSpeak 语音助手，请用中文简洁回复。"
    ctx-in-2: ""    # 空字符串 = 无默认值，不参与执行

效果：
  - 用户拖入 context_build 节点
  - ctx-in-1 端口未连线 → 自动使用预设的 system prompt
  - ctx-in-2 端口未连线 → 无默认值 → 不参与本次执行
  - 用户可以在端口配置中覆盖这个默认值
  - 一旦 ctx-in-1 连线，连线数据优先
```

### 5.5 端口被忽略的语义

当端口处于优先级 4（无连线、无配置、无默认值），该端口在本次节点执行中**不参与**：
- 节点代码读取该端口时得到 `None` 或空值
- 不阻止节点执行（即使该端口标记为 `always`）
- `always` 的真正语义是"始终可见"，不是"必须有数据才能执行"

数据就绪的判断标准是：**至少有一个数据输入端口有有效数据**，而非"所有 always 端口都有数据"。

### 5.6 多源合并（端口级简易操作）

在端口配置弹窗中，可以启用"多源合并"——将多路数据合为一路：

```
端口: ctx-in-stt
  多源合并: [开启]
  来源:
    [●] stt_listen.text-out
    [●] stt_history.hist-out
  合并方式: [拼接 ▾]  // 拼接 / 取最新 / 取最旧 / 列表
```

这是端口级的简易合并，不需要拖 merge 节点。适合简单的"把两路文本拼一起"场景。需要等待策略、超时、复杂格式化 → 用 merge 节点。

---

## 6. 透传与端口配对

### 6.1 透传的本质

透传是 Logic 节点的数据路由行为：**Logic 节点不修改数据内容，将上游数据原封不动地转发到下游。**

下游节点**不需要知道中间经过了 Logic 节点**——它收到的数据和直接从数据源连过来完全一样。

### 6.2 端口配对：一对一透传

用户的场景：`condition` 节点可能需要透传**多路**独立的数据流。

```
[stt_listen]──text────→ data-in-1 [condition] data-out-1 ──→ ctx-in-stt [context_build]
[ocr]────────text────→ data-in-2 [condition] data-out-2 ──→ ctx-in-ocr [context_build]
```

方案：**输入端口和输出端口配对。** 用户在 condition 节点上添加一对端口（`data-in-N` ↔ `data-out-N`），每对独立透传。

```
condition 端口定义：
  输入:
    ○ trigger-in (event)         — 触发信号
    group: data-in (repeatable, min=1, max=4)   — 数据输入组
    group: data-out (repeatable, min=0, max=4)  — 数据输出组，与 data-in 配对

配对规则：
  data-in-1 的数据 → 透传到 data-out-1
  data-in-2 的数据 → 透传到 data-out-2
  未配对的 data-in → 不转发（仅用于条件判断）

前端操作：
  点击 [添加透传对] → 同时创建 data-in-3 + data-out-3
  删除一对 → 同时移除
```

下游节点通过**端口名**区分不同来源的数据：
- `ctx-in-stt` 收到 condition 透传的 stt_listen 数据
- `ctx-in-ocr` 收到 condition 透传的 ocr 数据

### 6.3 透传配置

```
condition 节点的 data-out-N 端口：
  数据来源: [data-in-N ▾]  ← 指定透传哪个输入端口的原始数据
             [固定值]
             [节点属性]      ← 极少使用

默认：data-out-N 透传 data-in-N 的同编号端口
```

### 6.4 不经过透传的替代方案：数据线直连

如果数据不需要经过 condition 做条件判断，最简单的做法是**数据线直连绕过 condition**：

```
数据流：
  [stt_listen]──text-out──→ ctx-in-stt [context_build]

事件流（由引擎从数据连线推导，或手动创建纯事件连线）：
  [stt_listen]──done→ trigger-in [condition]──true→ trigger-in [context_build]
```

上下文构建节点直接从 stt_listen 取数据，condition 只控制触发时机。这是**数据线和事件线走不同路径**——流程图上同一张图的两层语义的自然表达。

---

## 7. 中间数据输出：meta-* 诊断端口

### 7.1 问题

节点执行过程中产生非主要产出、但对下游可能有价值的数据：
- `stt_listen`：触发了哪个关键词？置信度？累积了多少历史？
- `llm`：消耗了多少 token？思考过程（reasoning）？
- `ocr`：平均置信度？识别了多少区域？

### 7.2 方案：约定命名体系

不放在父类（每个节点类型的中间数据语义不同），也不随意命名（破坏可发现性）。约定统一前缀：

```
所有中间数据/诊断输出端口以 "meta-" 开头，全部标记为 `on-demand`（默认隐藏）。
```

```
stt_listen:
  meta-keyword (string)       — 触发的关键词
  meta-confidence (number)    — STT 置信度
  meta-history-count (number) — 累积历史条数

llm:
  meta-token-count (number)   — 消耗的 token 数
  meta-reasoning (string)     — 思考过程
  meta-model (string)         — 使用的模型名

ocr:
  meta-confidence (number)    — 平均置信度
  meta-region-count (number)  — 识别的文本区域数
```

**前端呈现**：meta 端口在 "+" 菜单中分组显示，有诊断图标：

```
[+] 菜单：
  ┌────────────────────────┐
  │ 数据端口               │
  │ + ctx-in-ocr           │
  │ + ctx-in-stt           │
  │ ─────────────          │
  │ 诊断端口               │
  │ + meta-keyword         │
  │ + meta-confidence      │
  └────────────────────────┘
```

### 7.3 使用示例

```
根据触发关键词选择不同的 LLM prompt：

  [stt_listen]──meta-keyword──→ data-in-1 [condition]
  condition 条件: data-in-1 == '求助'
    → true 触发"战术辅助"prompt 的 context_build
    → false 触发"日常闲聊"prompt 的 context_build
```

---

## 8. 变量系统：流程变量与系统变量

### 8.1 两级变量

| 变量类型 | 作用域 | 生命周期 | 读写方式 | 用途 |
|----------|--------|---------|---------|------|
| **流程变量** | 当前流程执行实例 | execution 开始 → 结束 | 节点产出写入 + 端口引用读取 | 跨节点共享中间结果 |
| **系统变量** | 全局 | 服务运行期间 | **专用节点 `sys_var`** 读写 | 全局配置、跨流程共享状态 |

### 8.2 流程变量

轻量、被动、无需专门节点。

**写入**：在节点的输出端口配置中勾选"写入流程变量"。

```
stt_listen 节点 → text-out 端口配置：
  写入流程变量: stt_last_text
stt_listen 节点 → meta-keyword 端口配置：
  写入流程变量: stt_last_keyword
```

引擎在节点产出数据后，自动将数据副本写入指定的流程变量。

**读取**：在输入端口的配置中引用 `$flow.变量名`。

```
context_build 节点 → ctx-in-stt 端口配置：
  数据来源: 流程变量 → $flow.stt_last_text
```

解析链中的位置（见 §5.2）：连线优先于流程变量。如果端口既有连线又配置了流程变量引用 → 连线生效，流程变量引用被忽略。只有断开连线后流程变量才生效。

**生命周期**：流程变量随 execution 创建而初始化，随 execution 结束而销毁。不同 execution 之间隔离。

### 8.3 系统变量节点 (sys_var)

系统变量**不是被动引用的全局变量池**——它有专门的节点来读写，因为读写系统变量本身就是一种数据处理动作。

```
节点类型: sys_var
行为模式: Transform（数据转换——它处理数据）

功能：读取、写入、更新全局系统变量。系统变量跨流程共享，持久化到磁盘。

端口：
  输入:
    ○ data-in (any)         — 要写入的值（仅 write/update 模式需要）
    ○ trigger-in (event)    — 触发信号

  输出:
    ● data-out (any)        — 读取的值（仅 read 模式产出）
    ● done (event)          — 操作完成

配置：
  操作模式: [read ▾]        — read / write / update
  变量名:   llm_model       — 系统变量名
  默认值:   gpt-4-turbo     — read 模式下变量不存在时返回的默认值
```

**三种操作模式**：

| 模式 | 触发后行为 | data-in 作用 | data-out 产出 |
|------|-----------|-------------|--------------|
| **read** | 读取系统变量值 | 不使用 | 变量值（或默认值） |
| **write** | 覆盖写入系统变量 | 要写入的值 | 不产出数据（仍发出 `done` 事件） |
| **update** | 合并更新（dict 场景）| 要合并的值 | 不产出数据（仍发出 `done` 事件） |

**使用示例**：

```
场景：LLM 节点执行前，从系统变量读取当前模型名

  [sys_var(read)]──data-out──→ model-in [llm]
  配置: 变量名=llm_model, 默认值=gpt-4-turbo

场景：用户通过前端修改了模型选择，写入系统变量

  [前端输入]──→ data-in [sys_var(write)]──done→ 触发 [llm]
  配置: 变量名=llm_model
```

### 8.4 系统变量持久化

系统变量写入时自动持久化到 `data/system_vars.json`。服务重启后恢复。前端可通过 WebSocket 消息 `sys_var.list` / `sys_var.get` 查询当前系统变量列表。

### 8.5 变量 vs 连线：选择指南

| 场景 | 推荐方案 |
|------|---------|
| 相邻节点的数据传递（A 产出 → B 直接消费） | 连线 |
| 跨多个节点的数据引用（A 产出 → D 消费，中间隔着 B、C） | 流程变量 |
| 多个节点需要同一份数据（扇出） | 连线（一条线连多个目标） |
| 全局配置（模型名、API key、阈值），需要在流程间共享 | 系统变量节点 |
| 调试/日志需要记录中间值 | 流程变量 |

---

## 9. 逻辑组件设计

### 9.1 逻辑组件的职责边界

**逻辑组件不转换数据，控制执行路径和数据路由。**

| 职责 | 说明 |
|------|------|
| **条件求值** | 根据表达式判断 true/false |
| **数据路由** | 将上游数据透传到对应下游 |
| **事件分发** | 将触发信号发送到正确分支 |
| **时序控制** | 延迟、聚合等待 |
| **外部通知** | 发送通知到前端/外部 |

### 9.2 condition — 条件分支

**端口定义**：
```
输入:
  ○ trigger-in (event)       — 触发信号
  group: data-in (repeatable, min=1, max=4)   — 数据输入组
  group: data-out (repeatable, min=0, max=4)  — 数据输出组（与 data-in 配对）

输出:
  ● true (event)             — 条件为真
  ● false (event)            — 条件为假（on-demand）
```

**配置项**：
- 条件表达式：Python 表达式，`data-in-1` 作为主判断变量
- false 端口可见性

**执行逻辑**：
1. 收到 trigger-in → 读取 data-in-1
2. 求值表达式
3. 所有已配对的 data-out-N → 透传对应 data-in-N 的原始数据
4. 触发 true 或 false 事件
5. 下游从 data-out 端口或直接数据连线读取数据

### 9.3 filter — 数据过滤（condition 的简化形态）

filter 是 condition 的一种**预设配置**，而非独立节点类型。实际运行时使用同一个 condition 引擎，但默认行为不同：

| 差异点 | condition | filter |
|--------|-----------|--------|
| false 分支端口 | 可选显示（`false` 端口） | 永久隐藏 |
| 拒绝行为 | 触发 `false` 事件 | 触发 `reject` 事件 |
| 语义侧重 | 二路分支 | 单路过滤 |

用户拖入 filter 节点时，实际创建的是一个 **`condition` 类型节点 + 预设配置**（`reject_behavior: "emit_reject_event"`, `false` 端口不可见）。这使得 filter 的使用体验更轻量，但底层不引入重复的逻辑。

**预设等效端口**（条件节点 + filter 预设）：
```
输入:
  ○ trigger-in (event)
  group: data-in (repeatable, min=1, max=4)

输出:
  ● pass (event)             — 通过
  ● reject (event)           — 拒绝
  group: data-out (repeatable, min=0, max=4)  — 透传
```

### 9.4 merge — 多路聚合

**端口定义**：
```
输入:
  ○ trigger-in (event, on-demand)
  group: data-in (repeatable, min=1, max=8)

输出:
  ● data-out (dict)          — 聚合数据: {"data-in-1": ..., "data-in-2": ...}
  ● done (event)             — 聚合完成
```

**配置项**：
- 聚合模式：`wait_all`（等所有已连接端口有数据）/ `wait_any`（任一有数据即触发）
- 超时时间：毫秒
- 聚合格式：`dict` / `list`

**简易合并（端口级配置）**：
如果只是简单地把两路数据合并为一路（不需要等待、超时等复杂逻辑），可以在目标节点的输入端口上直接配置"多源合并"，不需要拖 merge 节点：

```
context_build 的 ctx-in-stt 端口：
  多源合并: 开启
  来源: stt_listen.text-out + stt_history.hist-out
  合并方式: 拼接为字符串
```

简单合并走端口配置，复杂聚合走 merge 节点。

### 9.5 delay — 延迟等待

**设计变更**：delay 不再是独立的触发方式，而是**所有节点的通用修饰条件**。

任何节点都可以在配置中设置"执行前延迟"：

```
ocr 节点配置：
  触发方式: 事件连线触发
  执行前延迟: 500ms
```

如果需要独立的 delay 节点（在画布上显式表示等待），仍然提供轻量的 delay 节点：

```
delay 节点：
  输入: trigger-in (event), data-in (any, on-demand)
  输出: done (event), data-out (any, 透传 data-in)
  配置: 延迟时间(ms)
```

### 9.6 break — 循环中断

仅在 loop 子流程内部使用。收到触发后发出 `break` 事件，通知外层 loop 终止。

```
break 节点：
  输入: trigger-in (event)
  输出: break-out (event)
```

- 无需数据端口——break 不处理数据，只发控制信号
- 放在 loop 内部，当某个条件满足时触发（通常由 condition 节点的事件输出驱动）
- loop 监听到内部 break 事件后立即终止迭代

### 9.7 notify — 通知推送

```
notify 节点：
  输入: trigger-in (event), data-in (string, on-demand)
  输出: done (event)
  配置: 通知渠道(frontend/webhook/log)、级别(info/warning/error)、消息模板
```

### 9.8 简易操作：端口级 vs 逻辑节点级

| 操作 | 简单场景 | 复杂场景 |
|------|---------|---------|
| **合并** | 端口配置"多源合并"（拼接为字符串） | merge 节点（等待策略、超时、格式化） |
| **复制** | 数据线扇出（一条输出连多个目标） | 无需逻辑节点 |
| **过滤** | 端口配置"条件接收"（简单过滤表达式） | condition 节点（filter 预设） |
| **分支** | — | condition 节点 |
| **延迟** | 节点配置"执行前延迟" | delay 节点（显式画布表示） |

**合并方式选择决策树**：

```
需要合并多路数据？
│
├── 所有来源都来自连线？
│   └── 是 → 用"多源合并"（端口配置）
│
├── 需要等待条件（等全部 / 等任一）？
│   └── 是 → 用 merge 节点
│
├── 需要超时控制？
│   └── 是 → 用 merge 节点
│
├── 合并结果需要复杂格式化（非简单拼接）？
│   └── 是 → 用 merge 节点
│
└── 以上都不需要？
    └── 用"多源合并"（端口配置）——更简单

---

## 10. 子流程设计

### 10.1 核心思想

**子流程 = 一个节点，内部包含一个子画布。** 对外表现为普通节点，对内拥有独立的编辑空间。

### 10.2 类型

| 类型 | 说明 |
|------|------|
| **group** | 通用节点组——打包多个节点，对外暴露统一接口 |
| **loop** | 循环节点——循环执行内部节点 |

### 10.3 端口映射契约

外部端口和内部节点端口之间的映射：

```
默认映射（group）：
  外部 data-in → 内部第一个节点的 data-in
  外部 trigger-in → 内部第一个节点的 trigger-in
  内部最后一个节点的 data-out → 外部 data-out
  内部最后一个节点的 done → 外部 done

用户可在子流程配置面板中覆盖这些映射。
```

### 10.4 通用节点组 (group)

```
外部端口:
  ○ data-in (any), trigger-in (event)
  ● data-out (any), done (event)
```

**执行语义**：
1. 外部 trigger-in → 内部入口节点
2. 内部按连线顺序执行
3. 内部出口节点完成 → 映射到外部 data-out + done
4. 内部任意节点出错 → 组立即终止，外部 done 不触发

### 10.5 循环节点 (loop)

```
外部端口:
  ○ data-in (list), trigger-in (event), break-in (event, on-demand)
  ● data-out (list), iter (event), done (event)
```

**配置项**：
- 循环模式：`for-each` / `while` / `count`
- 最大迭代数：安全上限（默认 1000）
- 迭代间延迟：毫秒

**执行语义**：
1. 收到 trigger-in → 读取 data-in 列表
2. 每次迭代：
   a. 取当前元素 → 注入内部入口节点 data-in
   b. 触发内部入口节点 trigger-in
   c. 等待内部出口节点 done
   d. 收集出口 data-out 值
3. 全部完成 → 产出列表 → data-out → done

**跨迭代状态传递**：
循环内部节点可以读写流程变量 `$flow.loop_index`（当前索引）和 `$flow.loop_accumulated`（累积产出列表，只读）。如需跨迭代传递自定义状态，内部节点写入流程变量（如 `$flow.round_result`），下一迭代读取。

**中断**：
- 内部 break 节点的 break-out 事件 → 跳出循环
- 外部 break-in 端口收到事件 → 跳出
- 内部节点出错 → 默认终止循环

### 10.6 前端交互

- **展开/折叠**：双击节点进入内部画布，Esc 或面包屑返回上层
- **嵌套**：loop 内可含 group，group 内可含 loop
- **面包屑导航**：`主画布 > loop: 逐条处理 > group: OCR预处理`
- **模板保存**：右键节点组 → "保存为模板"

---

## 11. 数据类型与兼容性

### 11.1 数据类型

| data_type | 含义 | 典型产出者 |
|-----------|------|-----------|
| `image` | 图片数据 | input_image |
| `audio` | 音频数据 | ts_input, tts |
| `string` | 单条文本 | ocr, stt, llm |
| `string_array` | 文本列表 | stt_history |
| `messages` | LLM 消息数组 `[{role, content}]` | context_build |
| `event` | 事件信号 | 所有节点的 event-out 端口 |
| `any` | 任意类型（逻辑节点透传端口） | condition, filter |
| `number` | 数值 | meta 端口 |
| `list` | 列表 | loop data-in |
| `dict` | 字典 | merge data-out |

### 11.2 连线兼容性

| 源端口类型 | 可连接的目标端口类型 |
|-----------|-------------------|
| `any` | 任何类型 |
| `string` | `string`, `string_array`, `any` |
| `string_array` | `string_array`, `messages`, `any` |
| `messages` | `messages`, `any` |
| `event` | **仅** `event` |
| `list` | `list`, `any` |
| `dict` | `dict`, `any` |

**隐式转换**：
- `string` → `string_array`：自动包装为 `[string]`
- `string_array` → `messages`：自动转换为 `[{role: "user", content: joined}]`

---

## 12. 执行时机与错误传播

### 12.1 触发方式

每个节点执行前，引擎回答一个问题：**"你为什么该动了？"**

| 触发方式 | 机制 | 适用场景 |
|----------|------|----------|
| **数据就绪** | 至少一个数据输入端口有有效数据到达 | Transform、Sink（默认模式，覆盖 80% 场景） |
| **信号到达** | event 输入端口收到触发信号 | 被上游逻辑节点路由触发的节点 |
| **手动触发** | 用户点击执行按钮 | input_image、调试 |
| **常驻自触发** | 节点启动后进入无限循环 | stt_listen |

**延迟**不是第四种模式，而是**所有模式的通用修饰条件**：条件满足 + 延迟 N 毫秒 → 执行。

### 12.2 Listener 节点的执行契约

Listener（`stt_listen`）是特殊的 Source 节点，它不服从标准的 "trigger-in → execute → event-out" 模型：

```
Listener 执行契约：
  1. 流程启动时，Listener 自动开始执行（无需 trigger-in）
  2. 进入内部循环，自行管理执行节奏
  3. 每次循环迭代：
     a. 从总线/外部源获取数据（AudioBus、网络流等）
     b. 处理数据（STT 转写、关键词检测等）
     c. 如果满足触发条件（关键词匹配等）→ 产出数据 + 发出 done 事件
     d. 如果不满足 → 继续循环
  4. 流程停止或收到取消信号时退出循环
```

Listener 的 `done` 事件在每次触发时发出（可能多次），不像普通节点只发一次。

> **AudioBus 可见性**：AudioBus 是内部音频总线，仅在 `ts_input` 和 `stt_listen` 之间通过后端内存传递音频数据。AudioBus **不暴露为画布上的连线或端口**——它是后台基础设施，前端画布不渲染。用户只需知道 `ts_input` 和 `stt_listen` 配合作业即可。

### 12.3 错误传播策略

```
节点执行出错时：

  1. 节点状态 → ERROR，错误信息写入 node.error
  2. 该节点的 event-out 端口不触发（done/true/pass 等都不发出）
  3. 已连线的 data-out 不产出
  4. 依赖该节点触发事件的所有下游节点不会被执行
  
  5. 错误传播：
     - 组（group）内节点出错 → 组立即终止，外部 done 不触发
     - 循环（loop）内节点出错 → 默认终止循环（可配置为"记录错误继续"）
     - 独立节点出错 → 不影响同一流程中其他独立执行链

  6. 前端通知：错误信息通过 WebSocket 推送，节点卡片显示错误状态
```

**可选配置**：
- 节点可设置 `on_error: "skip"`（出错后继续触发 done，跳过此节点）
- 循环可设置 `on_iter_error: "continue"`（单次迭代出错继续下一次）

---

## 13. 配置分层

### 13.1 配置入口

| 配置入口 | 触发方式 | 内容 |
|----------|---------|------|
| **节点配置面板** | 双击节点 | 触发方式、业务参数、延迟、错误策略、流程变量写入 |
| **端口配置弹窗** | 点击端口 | 数据来源覆盖（连线/变量/固定值）、多源合并、数据类型限制 |
| **连线属性** | 点击连线 | 连线标签（可选） |

### 13.2 节点配置面板示例

```
┌─────────────────────────────────────────┐
│  节点配置: stt_listen                    │
│                                         │
│  ── 触发 ──                             │
│  触发方式:   [常驻自触发]                │
│                                         │
│  ── 业务参数 ──                         │
│  关键词:     [求助, 集合, 撤退]          │
│  引擎:       [sensevoice ▾]             │
│  采样率:     [16000]                     │
│                                         │
│  ── 流程变量写入 ──                     │
│  text-out → stt_last_text               │
│  meta-keyword → stt_last_keyword        │
└─────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────┐
│  节点配置: context_build                 │
│                                         │
│  ── 触发 ──                             │
│  触发方式:   [信号到达]                  │
│  执行前延迟: [0] ms                      │
│  错误策略:   [停止]                      │
│                                         │
│  ── 业务参数 ──                         │
│  最大上下文长度: [4096]                  │
└─────────────────────────────────────────┘
```

### 13.3 端口配置弹窗（点击端口触发）

```
端口状态：已连线

┌────────────────────────────┐
│  端口: ctx-in-stt          │
│  类型: string              │
│  连线: stt_listen.text-out │
│                            │
│  数据来源:                  │
│  [● 连线] ← 当前生效       │
│  [○ 流程变量]             │
│  [○ 固定值]               │
│                            │
│  多源合并: [关闭]          │
│                            │
│  [断开连线]                │
└────────────────────────────┘

端口状态：无连线，有默认值

┌────────────────────────────┐
│  端口: ctx-in-1            │
│  类型: string              │
│  连线: 无                  │
│                            │
│  数据来源:                  │
│  [○ 连线]                 │
│  [○ 流程变量]             │
│  [● 默认]                 │
│  当前值: 你是一个 TS 助手...│
│                            │
│  [编辑默认值]              │
└────────────────────────────┘

端口状态：无连线，用户手动配了流程变量

┌────────────────────────────┐
│  端口: ctx-in-stt          │
│  类型: string              │
│  连线: 无                  │
│                            │
│  数据来源:                  │
│  [○ 连线]                 │
│  [● 流程变量]             │
│  变量名: stt_last_text     │
│                            │
│  [更改为连线/固定值]       │
└────────────────────────────┘
```

### 13.4 连线属性

点击画布上的连线，弹出轻量信息面板：

```
┌─────────────────────────────────┐
│  连线                            │
│  from: stt_listen.text-out      │
│  to:   context_build.ctx-in-1   │
│  类型: 数据连线                  │
└─────────────────────────────────┘
```

### 13.5 流程级配置

每个流程（flow）除了节点和连线，还有自身的元配置。这些配置存储在 flow JSON 文件的顶层字段中。

```
PipelineDefinition {
  id: string              // 流程唯一 ID（文件名）
  name: string            // 流程显示名称
  description: string     // 流程描述（可选）
  group: string           // 所属分组（"游戏/暗区"）
  icon: string            // Material Symbols 图标名
  enabled: boolean        // 是否启用
  skill_prompt: string    // 流程级 skill prompt（可选，注入到 LLM 上下文）
  canvas: {
    width: int            // 画布宽度（默认 1700）
    height: int           // 画布高度（默认 1250）
  }
  nodes: NodeDefinition[]
  connections: ConnectionDef[]
}
```

**与当前代码的关系**：`backend/data/flows/*.json` 中的 flow 文件已包含这些字段（id, name, group, icon, enabled, skill_prompt, canvas）。`core/flow/manager.py` 中的 `FlowManager` 负责这些字段的 CRUD，groups 层级通过 `groups.json` 独立持久化。

---

## 14. 撤销/重做机制

### 14.1 设计原则

**所有编辑操作（节点增删移、连线增删、配置修改）都可撤销/重做。** 后端持有操作历史，前端发送 undo/redo 命令。

### 14.2 操作粒度

每次用户操作产生一笔历史记录：

| 操作 | 记录内容 | 合并策略 |
|------|---------|---------|
| `node.create` | 节点完整快照 | 不合并 |
| `node.delete` | 节点完整快照（含连线） | 不合并 |
| `node.move` | node_id, old_position, new_position | **500ms 窗口内合并**（同一 node_id 的连续拖拽只保留首尾） |
| `node.update_config` | node_id, old_config, new_config | **500ms 窗口内合并**（同一 node_id 的连续输入合并为一次） |
| `connection.create` | 连线完整快照 | 不合并 |
| `connection.delete` | 连线完整快照 | 不合并 |

### 14.3 持久化

```
每个 flow 独立维护历史：
  backend/data/history/
    <flow_id>.jsonl        # 每行一条记录，append-only

每条记录格式：
  {
    "ts": 1715000000.123,
    "action": "node.move",
    "flow_id": "暗区竞标赛",
    "undo": { "node_id": "n3", "position": {"x": 100, "y": 200} },
    "redo": { "node_id": "n3", "position": {"x": 250, "y": 300} }
  }
```

- 每 flow 最多 100 条历史记录，超出后移除最旧的
- 新建操作会丢弃当前位置之后的所有记录（无法 redo 已丢弃的未来）
- 500ms 合并窗口：同一 node_id 的连续移动/配置更新合并为首尾两条

### 14.4 前端交互

- `Ctrl+Z` → 发送 `undo` 命令
- `Ctrl+Y` / `Ctrl+Shift+Z` → 发送 `redo` 命令
- 后端返回 `history.state` 事件（`{ can_undo, can_redo }`），前端据此禁用/启用按钮

> **与当前代码的关系**：此机制已在 `core/history/manager.py` (`HistoryManager`) 中完整实现。前端 `stores/editor.js` 通过 `undo()`/`redo()` 方法发送 WS 命令，`onHistoryState()` 更新按钮状态。

---

## 15. 运行时状态映射

### 15.1 节点状态

每个节点在运行时处于以下状态之一：

| 状态 | 含义 | 边框 | 状态点 | 动画 |
|------|------|------|--------|------|
| **PENDING** | 等待触发，尚未执行 | `border-outline`（灰色半透明） | 灰色 | 无 |
| **PROCESSING** | 正在执行中 | `border-primary`（蓝色） | 蓝色呼吸脉冲 | `nodePulse` 动画（蓝色光晕） |
| **COMPLETED** | 执行成功完成 | `border-secondary`（绿色） | 绿色 | 无 |
| **ERROR** | 执行出错 | `border-error`（红色） | 红色 | 无 |
| **LISTENING** | 常驻监听中（仅 Listener） | `border-primary`（蓝色） | 蓝色呼吸脉冲 + 关键词检测点（橙色） | `pulse` + `keywordPulse` |

### 15.2 状态转换规则

```
PENDING → PROCESSING → COMPLETED   （正常执行）
                     → ERROR        （执行失败）

LISTENING 是特殊状态（仅 stt_listen）：
  LISTENING → 每次关键词命中 → 触发下游，自身保持 LISTENING
  LISTENING → 流程停止 → PENDING
```

### 15.3 前端组件映射

| 状态 | NodeCard CSS class | IOPort 状态 | 进度条 |
|------|-------------------|-------------|--------|
| PENDING | `border-outline` | `disconnected`（无连线）/ `connected`（有连线） | 隐藏 |
| PROCESSING | `border-primary node-pulse` | `flowing`（数据流端口） | 显示，实时更新 |
| COMPLETED | `border-secondary` | `connected` | 隐藏 |
| ERROR | `border-error` | `connected`（保持连线状态） | 隐藏 |
| LISTENING | `border-primary` | `flowing`（音频输入端口） | 隐藏 |

> **与当前代码的关系**：`NodeCard.vue` 中 `borderClass`、`statusClass`、`statusLabel`、`isProcessing`、`isListening` 等计算属性已实现此映射。`execution.js` 中 `nodeStatuses` 存储各节点运行时状态。

---

## 16. 设计总结

### 16.1 与 v0.5 / v1.x 的关键变更

| 旧设计 | v2.0 | 变更原因 |
|--------|------|----------|
| data/event/data+event 三种连线类型 | `type: "data"|"event"` 两种，事件关系由数据连线推导 | 视图是滤镜——type 决定连线在哪个视图可见，而非分离的连线系统 |
| 事件关系需要显式创建 | 数据连线**天然隐含**事件关系，事件视图下推导渲染 | 数据到达 = 触发，这是默认行为，不应要求用户手动维护 |
| TriggerConfig + InputMapping + ConnectionDef 三套系统 | 统一为 ConnectionDef（见 §17 迁移路径） | 连线同时表达数据来源、触发关系，消除并行配置系统 |
| 透传 = 输出节点属性值 | 透传 = **端口配对**（data-in-N ↔ data-out-N 1:1） | 明确路由语义，支持多路独立透传 |
| 无变量系统 | **流程变量 + 系统变量**（$flow.* / sys_var 节点） | 跨节点数据引用不依赖连线，避免画布意大利面 |
| 输入来源是用户三选一 | 输入来源是**引擎解析链**（连线 → 变量 → 固定值 → 模板预设） | 简化用户操作，用户只需连线或填值 |
| delay 是独立触发方式 | delay 是**所有节点的通用修饰条件** | 任何节点都可以延迟执行 |
| filter 是独立节点 | filter 是 **condition 的预设简化形态** | 消除重复逻辑引擎，保留更轻的使用体验 |
| 所有端口同等对待 | `repeatable` 端口组 + `always`/`on-demand` 可见性 | 精确控制哪些端口可以多实例 |
| 端口操作为零 | **端口级简易操作**（多源合并、条件接收） | 简单场景不拖逻辑节点 |
| 无中间数据机制 | `meta-*` 诊断端口 | 标准化中间数据输出 |
| 无 break 节点 | loop 内部 **break 节点** | 循环中断显式可控 |
| 错误处理未定义 | 明确错误传播策略 + skip/continue 配置 | |
| 无撤销/重做 | **HistoryManager**（JSONL 持久化, 500ms 合并窗口） | 所有编辑可逆 |
| 无运行时状态映射 | **5 种状态**（PENDING/PROCESSING/COMPLETED/ERROR/LISTENING）→ UI 视觉映射 | 前后端状态契约一致 |

### 16.2 核心数据模型

```
PortDef {
  id: string
  label: string
  data_type: string
  visibility: "always" | "on-demand"
  group: string | null        // 端口组名（repeatable 时共用）
  repeatable: boolean
  min: int | null
  max: int | null
  multi: boolean
}

NodeTypeDef {
  type: string
  name: string
  icon: string
  color: string
  ports: { inputs: PortDef[], outputs: PortDef[] }
  default_config: dict
  tabs: TabDef[]
}

NodeDefinition {
  id: string
  type: string
  name: string
  position: {x, y}
  config: {
    trigger_mode: "data-ready" | "signal" | "manual" | "always-on"
    delay_ms: int
    on_error: "stop" | "skip"
    port_fixed_values: { "port_id": "value or $flow.var or $sys.var" }
    port_data_sources: { "port_id": { type: "connection" | "variable" | "fixed" | "attribute", value: "..." } }
    // ... 业务参数
  }
  visible_ports: string[]
  flow_var_writes: { "var_name": "port_id" }   // 产出写入流程变量
}

ConnectionDef {
  id: string
  from_node: string
  from_port: string
  to_node: string
  to_port: string
  type: "data" | "event"     // 用于前端视图分组 + 引擎执行推导
}
```

### 16.3 节点类型总览

| 类型 | 行为模式 | 关键输入 | 关键输出 | 子流程 |
|------|----------|---------|---------|--------|
| `input_image` | Source | — | img-out, done | 否 |
| `ts_input` | Source | — | audio-out, done | 否 |
| `ocr` | Transform | img-in, trigger-in | text-out, done | 否 |
| `stt` | Transform | audio-in, trigger-in | text-out, done | 否 |
| `stt_history` | Transform | hist-in, trigger-in | hist-out, hist-trigger | 否 |
| `context_build` | Transform | ctx-in (repeatable), trigger-in | msg-out, done | 否 |
| `llm` | Transform | msg-in, trigger-in | text-out, done | 否 |
| `tts` | Transform | text-in, trigger-in | audio-out, done | 否 |
| `sys_var` | Transform | data-in, trigger-in | data-out, done | 否 |
| `ts_output` | Sink | audio-in, trigger-in | done | 否 |
| `stt_listen` | Listener | —（订阅AudioBus） | text-out, done, meta-* | 否 |
| `condition` | Logic | trigger-in, data-in (repeatable) | data-out (repeatable), true, false | 否 |
| `filter` | Logic（condition 预设） | trigger-in, data-in (repeatable) | data-out (repeatable), pass, reject | 否 |
| `merge` | Logic | data-in (repeatable), trigger-in | data-out, done | 否 |
| `delay` | Logic | trigger-in, data-in | data-out, done | 否 |
| `break` | Logic | trigger-in | break-out | 否 |
| `notify` | Logic | trigger-in, data-in | done | 否 |
| `group` | SubFlow | data-in, trigger-in | data-out, done | 是 |
| `loop` | SubFlow | data-in, trigger-in, break-in | data-out, iter, done | 是 |

---

## 17. 迁移附录

### 17.1 当前代码 → 目标设计的迁移路径

当前代码中存在三个并行系统描述节点间的依赖关系：`TriggerConfig`、`InputMapping`、`ConnectionDef`。目标设计将它们统一为 `ConnectionDef` + 引擎推导。

#### TriggerConfig → ConnectionDef 迁移

当前 `NodeDefinition.trigger`（`TriggerConfig`）的 `source_node` 字段指定了一个节点的完成事件触发另一个节点。在目标设计中：

```
旧:  Node A 的 trigger.source_node = "node_b_id"
新:  创建 ConnectionDef { from_node: "node_b_id", from_port: "done", to_node: "node_a_id", to_port: "trigger-in", type: "event" }
```

如果数据连线的 `from_node` 已经是 `node_b_id`，则引擎自动推导触发关系，**无需额外创建 event 连线**。

#### InputMapping → ConnectionDef 迁移

当前 `NodeDefinition.input_mappings` 的 `from_node` / `from_port` 指定了数据来源。在目标设计中：

```
旧:  Node A 的 input_mapping = { from_node: "node_b_id", from_port: "text-out" }
新:  创建 ConnectionDef { from_node: "node_b_id", from_port: "text-out", to_node: "node_a_id", to_port: "text-in", type: "data" }
```

#### ConnectionDef.type 迁移

当前代码中 `ConnectionDef.type` 为三值 `"data" | "event" | "trigger"`：

```
"data"    → "data"    （不变）
"event"   → "event"   （不变）
"trigger" → "event"   （"trigger" 合并入 "event"，触发语义由引擎从 data 连线推导）
```

#### 迁移步骤建议

1. **不改现有存储**：`data/flows/*.json` 中的 `trigger` 和 `input_mappings` 字段暂时保留
2. **引擎双读**：新引擎同时读取旧字段和新 ConnectionDef，新格式优先
3. **写入时升级**：保存 flow 时写入新格式（ConnectionDef），移除旧字段
4. **清理**：下一个大版本移除双读逻辑

### 17.2 v2.0 → v2.1 变更清单

| 变更 | 说明 |
|------|------|
| `importance` → `visibility` | PortDef 字段重命名：`"required"/"optional"` → `"always"/"on-demand"` |
| `ConnectionDef.type` 保留 | v2.0 去掉了 type，v2.1 恢复为 `"data"|"event"`（前端依赖） |
| `"trigger"` 废弃 | 合并入 `"event"`，引擎从 data 连线推导触发关系 |
| filter → condition 预设 | filter 不再是独立节点类型，是 condition + 预设配置 |
| 新增 break 节点 | loop 内部循环中断 |
| 新增 stt_history | 继承 STT 历史累积 + 关键词判断（代码中已存在） |
| 新增流程级配置节 | flow 名称、描述、分组、图标、画布尺寸、skill_prompt |
| 新增撤销/重做节 | HistoryManager 设计：JSONL 持久化、500ms 合并窗口 |
| 新增运行时状态映射 | PENDING/PROCESSING/COMPLETED/ERROR/LISTENING → UI 视觉映射 |
| sys_var write done 事件 | 明确 write/update 模式 data-out 不产出数据，但 done 事件正常发出 |
