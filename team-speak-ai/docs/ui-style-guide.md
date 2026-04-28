# TeamSpeak AI UI 样式规范

> 提取自 `frontend/docs/pipeline-prototype.html`，作为前端统一风格基准。

---

## 1. 颜色系统

采用 **Material Design 3 (Material You) 暗色主题** 色板，基于 Tailwind CSS 扩展。

### 1.1 语义色

#### Primary（蓝色 —— 数据流通、活跃状态、选中标签）

| Token | 色值 | 用途 |
|---|---|---|
| `primary` | `#adc7ff` | 活跃 tab、正在处理的节点边框、事件流箭头、SVG 连接线标签 |
| `on-primary` | `#002e68` | primary 前景色（按钮文字） |
| `primary-container` | `#4a8eff` | 品牌强调色、logo、流式光标、section 强调条、流式数据线 |
| `on-primary-container` | `#00285b` | primary-container 前景色 |
| `inverse-primary` | `#005bc0` | 反色场景 |
| `primary-fixed` | `#d8e2ff` | hover 态 |
| `primary-fixed-dim` | `#adc7ff` | 暗色 fixed |
| `on-primary-fixed` | `#001a41` | fixed 前景 |
| `on-primary-fixed-variant` | `#004493` | fixed variant 前景 |

#### Secondary（绿色 —— 就绪状态、已连接、成功）

| Token | 色值 | 用途 |
|---|---|---|
| `secondary` | `#4edea3` | 就绪状态点、数据流箭头(静态)、上传节点边框、成功信息 |
| `on-secondary` | `#003824` | secondary 前景色 |
| `secondary-container` | `#00a572` | 已连接端口（静态）、二级容器 |
| `on-secondary-container` | `#00311f` | container 前景色 |
| `secondary-fixed` | `#6ffbbe` | hover 态 |
| `secondary-fixed-dim` | `#4edea3` | （同 secondary） |
| `on-secondary-fixed` | `#002113` | fixed 前景 |
| `on-secondary-fixed-variant` | `#005236` | fixed variant 前景 |

#### Tertiary（橙色 —— 关键词、触发条件、告警）

| Token | 色值 | 用途 |
|---|---|---|
| `tertiary` | `#ffb695` | 触发关键词标签 |
| `on-tertiary` | `#571e00` | tertiary 前景色 |
| `tertiary-container` | `#ef6719` | 关键词高亮、关键词判断节点边框/步骤号、条件箭头 |
| `on-tertiary-container` | `#4c1a00` | container 前景色 |
| `tertiary-fixed` | `#ffdbcc` | hover 态 |
| `tertiary-fixed-dim` | `#ffb695` | 暗色 fixed |
| `on-tertiary-fixed` | `#351000` | fixed 前景 |
| `on-tertiary-fixed-variant` | `#7c2e00` | fixed variant 前景 |

#### Error（红色 —— 错误、删除、危险操作）

| Token | 色值 | 用途 |
|---|---|---|
| `error` | `#ffb4ab` | 错误提示文字 |
| `on-error` | `#690005` | error 前景色 |
| `error-container` | `#93000a` | 错误背景容器 |
| `on-error-container` | `#ffdad6` | container 前景色 |

### 1.2 表面色（Surface Elevation 层级）

从低到高：

| Token | 色值 | 用途 |
|---|---|---|
| `background` | `#10131b` | 页面背景 |
| `surface` / `surface-dim` | `#10131b` | 最暗表面层 |
| `surface-container-lowest` | `#0b0e16` | 最低抬升容器（内嵌代码块、日志背景） |
| `surface-container-low` | `#181c23` | 低抬升容器 |
| `surface-container` | `#1c2027` | 默认容器（玻璃节点背景） |
| `surface-container-high` | `#272a32` | 高抬升容器 |
| `surface-container-highest` | `#31353d` | 最高抬升容器 |
| `surface-variant` | `#31353d` | 表面变体（进度条背景、滚动条 thumb、标签背景） |
| `surface-bright` | `#363942` | 最亮表面层 |

### 1.3 表面文本色

| Token | 色值 | 用途 |
|---|---|---|
| `on-surface` | `#e0e2ed` | 主要文字 |
| `on-surface-variant` | `#c1c6d7` | 次要/辅助文字 |
| `inverse-surface` | `#e0e2ed` | 反色表面 |
| `inverse-on-surface` | `#2d3039` | 反色文字 |

### 1.4 边框色

| Token | 色值 | 用途 |
|---|---|---|
| `outline` | `#8b90a0` | 默认边框、节点分割线、tab 文字、节点标题图标 |
| `outline-variant` | `#414754` | 弱边框、分割线变体 |

### 1.5 增强色（Tailwind Slate 扩展，用于特殊场景）

| 色值 | 用途 |
|---|---|
| `#020617` (slate-950) | 右侧详情面板背景、顶部导航栏 |
| `#0f172a` (slate-900) | 侧栏 hover |
| `#1e293b` (slate-800) | 缩放按钮 hover |
| `#64748b` (slate-500) | 日志时间戳、弱化元数据 |
| `#94a3b8` (slate-400) | 侧栏未激活项、未激活链接 |
| `#cbd5e1` (slate-300) | 次级侧栏标题 |
| `#e2e8f0` (slate-200) | 侧栏已展开标题 |

### 1.6 颜色使用规则

- **禁止**在组件代码中直接写裸色值（如 `#adc7ff`、`#4edea3`），必须使用 Tailwind token 或 CSS 变量。
- Primary 系 **仅用于数据流通/活跃状态**，不可用于装饰。
- Secondary 系 **仅用于就绪/成功/已连接**。
- Tertiary 系 **仅用于触发条件/关键词/告警**。
- Outline 系 **仅用于边框和分割线**。

---

## 2. 字体系统

### 2.1 字体家族

| 角色 | 字体栈 | 使用范围 |
|---|---|---|
| UI 正文 | `'Inter', sans-serif` | 主体文字、标题、按钮、状态栏 |
| 代码/标签 | `'Space Grotesk', sans-serif` | 标签、徽章、tab、时间戳、版本号、命令行输出、端口标签、SVG 连接线标签 |

### 2.2 字号阶梯

| 级别 | 字号 | 行高 | 字重 | 字间距 | 对应 CSS Class |
|---|---|---|---|---|---|
| H1 | 32px | 1.2 | 600 | -0.02em | `font-h1` |
| H2 | 24px | 1.3 | 600 | normal | `font-h2` |
| Body | 16px | 1.6 | 400 | normal | `font-body-main` |
| Body-Sm | 14px | 1.5 | 400 | normal | `font-body-sm` |
| Code Label | 12px | 1.0 | 500 | 0.05em | `font-code-label` |
| Node Title | 13px | 1.2 | 600 | normal | `font-node-title` |

### 2.3 场景级字号

以下通过内联 `font-size` 或 Tailwind utility 应用：

| 场景 | 字号 | 字重 | 字间距 | 家族 |
|---|---|---|---|---|
| Logo / 应用名 | 18px (`text-lg`) | 700 (`font-bold`) | `tracking-tight` | Inter |
| 侧栏标题 | 14px (`text-sm`) | 500 (`font-medium`) | normal | Inter |
| 节点标题 | 13px | 600 | normal | Inter（`font-node-title`） |
| 节点内标签/徽章 | 12px | 500 | 0.05em | Space Grotesk（`font-code-label`） |
| Tab 按钮文字 | 11px | 500 | 0.05em | Space Grotesk |
| 流程图切换按钮 | 10px | 500/600 | 0.05em | Space Grotesk |
| 侧栏子项 | 11px | 400 | normal | Inter |
| 状态栏文字 | 10px | 500 | `tracking-widest` | Inter |
| 图例标题 | 10px | bold | 0.2em, uppercase | Space Grotesk |
| 面板标签 | 11px | 500 | 0.05em | Space Grotesk |
| 端口悬停标签 | 9px | 400 | normal | Space Grotesk |
| SVG 连接线标签 | 10px | 500 | normal | Space Grotesk |
| 日志行 | 10px | 500 | normal | Space Grotesk |
| 版本号 | 10px | 500 | 0.05em | Space Grotesk |
| 进度条标签 | 9px | 500 | normal | Space Grotesk |
| 设置面板按钮 | 14px | 500 | normal | Inter |

---

## 3. 间距与布局

### 3.1 间距阶梯

基于 4px 基准：

| Token | 值 | Tailwind 对应 |
|---|---|---|
| `unit` | 4px | `p-1` / `gap-1` |
| `xs` | 4px | |
| `sm` | 8px | `p-2` / `gap-2` |
| `md` | 16px | `p-4` / `gap-4` |
| `lg` | 24px | `p-6` / `gap-6` |
| `xl` | 32px | `p-8` / `gap-8` |
| `panel-padding` | 20px | 右侧详情面板内边距 |
| `grid-gutter` | 16px | 网格间隔 |

### 3.2 圆角

| Token | 值 | 用途 |
|---|---|---|
| `DEFAULT` | 2px (0.125rem) | 最小圆角 |
| `lg` | 4px (0.25rem) | 流程图切换按钮、端口标签背景 |
| `xl` | 8px (0.5rem) | 节点卡片、详情面板、控制栏 |
| `full` | 9999px | 胶囊形标签（`rounded-full`） |

### 3.3 关键布局尺寸

| 元素 | 宽 | 高/位置 |
|---|---|---|
| 顶部导航栏 | 100% (fixed) | 56px |
| 左侧边栏 | 256px (w-64, fixed) | top:56px, bottom:32px |
| 右侧详情面板 | 320px (fixed) | top:56px, bottom:32px |
| 底部状态栏 | 100% (fixed) | 32px |
| 主画布区域 | flex-1, ml-64 | 可滚动 |
| 画布 | 1700px | 1250px（可缩放） |
| 节点卡片宽度 | 220px / 250px / 280px / 320px | 取决于节点复杂度 |
| 工作流徽章 | 24px × 24px | 圆形，位于节点右上角 -10px 偏移 |
| I/O 端口 | 14px × 14px | 圆形 |
| 缩放控制栏 | auto | 位于 left:272px, bottom:48px |

---

## 4. 毛玻璃效果

### 4.1 节点卡片玻璃

```css
.glass-node {
  background: rgba(28, 32, 39, 0.92);  /* surface-container @ 92% */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
```

### 4.2 半透明模糊面板

| 位置 | CSS |
|---|---|
| 顶部导航栏 | `bg-slate-950/80 backdrop-blur-xl` |
| 左侧边栏 | `bg-slate-950/90 backdrop-blur-2xl` |
| 底部缩放控制栏 | `bg-slate-950/80 backdrop-blur-md` |

### 4.3 右侧详情面板

- 背景 `#020617`（slate-950），无透明度，无模糊 —— 完全不透明。

---

## 5. 组件规范

### 5.1 NodeCard（节点卡片）

**基础结构：**
```
┌─────────────────────────────┐
│ ● I/O Port          [①] 徽章│ ← 工作流步骤号
│ [icon] 节点标题              │ ← header (border-b)
├─────────────────────────────┤
│ [tab] [tab] [tab]           │ ← 可选 tab bar (border-b)
├─────────────────────────────┤
│ 状态行 / 标签组 / 数据块     │ ← body (p-3, space-y-2)
└─────────────────────────────┘
```

**CSS 类：**
- `absolute` 定位在画布上
- `glass-node` 背景 + 模糊
- `rounded-xl` (8px)
- `border` 外框，颜色按节点状态变化
- `z-10` 基础层级
- `node-card` 交互类（见下方）
- 无 tab 的节点 body 为 `p-3 space-y-2`
- 有 tab 的节点 body 在 `.node-tab-content` 中

**边框颜色语义：**

| 状态 | Border Class |
|---|---|
| 就绪/可操作 | `border-secondary/40` 或 `border-secondary/30` |
| 已连接待命中 | `border-secondary-container/30` |
| 处理中 | `border-2 border-primary node-pulse` |
| 被触发/构建中 | `border-primary/50` |
| 空闲/待命 | `border-outline-variant/50` |

**交互：**

```css
.node-card {
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.node-card:hover {
  transform: translateY(-2px);
  z-index: 20 !important;
}
```

**宽度建议：**

| 节点类型 | 推荐宽度 |
|---|---|
| 简单节点（Upload, OCR, TS Input/Output, TTS） | 220px |
| 中等节点（ContextBuild, LLM） | 250px |
| 复杂双列节点（History） | 280px |
| 多 Tab 处理节点（STT） | 320px |

背景为 `glass-node` 或 `bg-surface-container/90`。

### 5.2 NodeCard Header

```
flex items-center gap-2 px-3 py-2 border-b border-outline-variant/50
├── Material Symbol icon (text-sm, 对应功能色)
├── Title (font-node-title text-node-title text-on-surface)
└── [可选] 右侧标签/状态点
```

### 5.3 Tab 系统

#### 节点内 Tab（.tab-btn）

```css
.tab-btn {
  position: relative;
  padding: 6px 12px;
  font-size: 11px;
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em;
  font-weight: 500;
  color: #8b90a0;                    /* outline */
  cursor: pointer;
  transition: color 0.2s;
  border-bottom: 2px solid transparent;
}
.tab-btn:hover { color: #c1c6d7; }   /* on-surface-variant */
.tab-btn.active {
  color: #adc7ff;                     /* primary */
  border-bottom-color: #adc7ff;       /* primary */
}
```

#### 右侧面板 Tab（.detail-tab-btn）

与 `.tab-btn` 相同的基础样式，但：
- `flex: 1; padding: 8px 0; text-align: center`
- 无 hover 背景变化

#### Tab 内容面板

```css
.node-tab-content { display: none; }
.node-tab-content.active { display: block; }
```

### 5.4 按钮

#### 流程图切换按钮（.flow-toggle-btn）

```css
.flow-toggle-btn {
  padding: 4px 10px;
  font-size: 10px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: #8b90a0;
  cursor: pointer;
  border-radius: 4px;
  background: transparent;
  border: none;
  transition: color 0.2s, background 0.2s;
}
.flow-toggle-btn:hover {
  color: #c1c6d7;
  background: rgba(255, 255, 255, 0.05);
}
.flow-toggle-btn.active {
  color: #adc7ff;
  background: rgba(173, 199, 255, 0.12);
  font-weight: 600;
}
```

#### 缩放按钮

```
28px × 28px (w-7 h-7)
flex items-center justify-center
color: #94a3b8 (hover: #60a5fa)
background: transparent (hover: #1e293b/50)
border-radius: 4px
transition: all; active: scale(0.9)
```

#### 面板操作按钮

**取消：** `bg-surface-variant text-on-surface px-4 py-2 rounded-lg text-sm font-medium border border-outline-variant hover:bg-surface-container-highest transition-colors`

**保存：** `bg-primary text-on-primary px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-fixed transition-colors`

#### 侧栏按钮

- 展开/折叠：`w-full flex items-center justify-between px-3 py-2 rounded hover:bg-slate-900/50 transition-all`
- 子项：`w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-slate-900/50 transition-all`
- 当前激活项：`text-primary border-l-2 border-primary bg-primary/5`

### 5.5 I/O 端口（.io-port）

**仅**在"全部"和"数据流"视图中显示（`.data-only` 类）。

```css
.io-port {
  position: absolute;
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2.5px solid #8b90a0;   /* outline */
  background: #10131b;             /* surface */
  z-index: 35;
  cursor: pointer;
  transition: all 0.2s ease;
}
.io-port:hover {
  transform: scale(1.5);
  z-index: 60;
}
```

**定位：** 输入端口 `left: -7px`，输出端口 `right: -7px`，垂直位置由 style 属性指定。

**状态：**

| 状态 | Class | 边框色 | 背景 | 阴影 |
|---|---|---|---|---|
| 未连接 | `.disconnected` | `#8b90a0` | `#10131b` | 无 |
| 已连接 | `.connected` | `#4edea3` | `rgba(78,222,163,0.12)` | `0 0 8px rgba(78,222,163,0.3)` |
| 数据流通 | `.flowing` | `#4a8eff` | `rgba(74,142,255,0.18)` | `0 0 12px rgba(74,142,255,0.5)` + portFlowPulse 动画 |

#### 端口悬停标签（.io-label）

```css
.io-label {
  position: absolute;
  font-size: 9px;
  font-family: 'Space Grotesk', sans-serif;
  white-space: nowrap;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  color: #c1c6d7;                          /* on-surface-variant */
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  background: rgba(11, 14, 22, 0.95);       /* surface-container-lowest */
  padding: 3px 7px;
  border-radius: 3px;
  border: 1px solid #31353d;               /* surface-variant */
  z-index: 50;
}
.io-port:hover .io-label {
  opacity: 1;
  pointer-events: auto;
}
```

### 5.6 工作流徽章（.workflow-badge）

```
position: absolute
top: -10px; right: -10px   (突出节点右上角)
width: 24px; height: 24px
border-radius: 50%
display: flex; align-items: center; justify-content: center
font-size: 11px; font-weight: bold
font-family: 'Space Grotesk'
z-index: 40
border: 2px solid
background: #10131b
color: 与 border 同色
```

颜色与节点步骤圆圈一致（primary/secondary/tertiary-container）。

### 5.7 标签/芯片

**选中/激活标签：**
```
px-2 py-0.5 rounded-full
bg-{color}/10 text-{color}
text-[10px] font-code-label
border border-{color}-container/30
```

**未选中标签：**
```
px-2 py-0.5 rounded-full
bg-surface-variant text-outline-variant
text-[10px] font-code-label
```

**关键词触发标签：**
```
px-2 py-0.5 rounded-full
bg-tertiary-container/10 text-tertiary-container
text-[10px] font-code-label
border border-tertiary-container/30
```

### 5.8 数据块文本

```
p-1.5 bg-surface-container-lowest rounded
text-[11px] text-outline-variant font-code-label
```

### 5.9 状态指示点

- 就绪/运行：`w-1.5 h-1.5 rounded-full bg-secondary` + `shadow-[0_0_8px_rgba(78,222,163,0.6)]` + `animate-pulse`
- 处理中：`w-1.5 h-1.5 rounded-full bg-primary` + `shadow-[0_0_8px_rgba(173,199,255,0.6)]` + `animate-pulse`
- 待命：`w-1.5 h-1.5 rounded-full bg-outline-variant`（无动画，无阴影）

### 5.10 进度条

**细条：**
```
w-full bg-surface-variant rounded-full h-1
  > .fill: bg-primary h-1 rounded-full style="width: X%"
```

**超细条：**
```
w-full bg-surface-variant rounded-full h-0.5
  > .fill: bg-primary h-0.5 rounded-full style="width: X%"
```

---

## 6. SVG 连接线

### 6.1 箭头标记（Arrow Marker）

需要在 SVG `<defs>` 中预定义：

| Marker ID | 填充色 | 透明度 | 用途 |
|---|---|---|---|
| `arrowEvent` | `#adc7ff` (primary) | 0.6 | 事件流箭头 |
| `arrowData` | `#4edea3` (secondary) | 0.8 | 数据流箭头（绿色） |
| `arrowDataFlow` | `#4a8eff` (primary-container) | 0.8 | 活跃数据流箭头（蓝色） |

**标记形状：**
```svg
<marker markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
  <polygon points="0,2 10,5 0,8" fill="..." opacity="..."/>
</marker>
```

### 6.2 线型

| 类型 | 样式 | 用途 |
|---|---|---|
| 数据流（静态） | `stroke="#4edea3" stroke-width="2.5" stroke-dasharray="10 5" class="flow-line"` | 数据传递 |
| 数据流（活跃） | `stroke="#4a8eff" stroke-width="2.5" class="flow-line"` | 数据处理中 |
| 事件流 | `stroke="#adc7ff" stroke-width="2.5" marker-end="url(#arrowEvent)"` | 触发/事件传递 |
| 条件分支（关键词不匹配） | `stroke="#ef6719" stroke-width="1.8" stroke-dasharray="6 4" opacity="0.7"` | 条件回环 |
| 循环回路 | `stroke="#4edea3" stroke-width="1.8" class="loop-line" opacity="0.45"` | 流程循环 |
| 弱数据流（OCR） | `stroke="#4edea3" stroke-width="2" stroke-dasharray="10 5"` | 慢速/异步数据 |

### 6.3 连接线标签背景

```svg
<rect class="lbl-bg"/>  <!-- fill: rgba(11,14,22,0.92), rx: 3, ry: 3 -->
```

尺寸由文本决定，放在文本下方。

### 6.4 连接线标签文字

```svg
<text
  x="..." y="..."
  text-anchor="middle"
  fill="同线色"
  font-size="10"
  font-family="Space Grotesk"
  font-weight="bold/normal"
>标签文字</text>
```

### 6.5 步骤圆圈

所有视图均可见：

```svg
<circle cx="..." cy="..." r="13"
  fill="{color}" opacity="0.15"
  stroke="{color}" stroke-width="1.5"/>
<text x="..." y="..." text-anchor="middle"
  fill="{color}" font-size="12" font-weight="bold"
  font-family="Space Grotesk">①</text>
```

颜色：secondary（绿）= 输入/输出/合成，primary（蓝）= 处理节点，tertiary-container（橙）= 判断节点。

### 6.6 贝塞尔曲线规范

跨行连接使用 Cubic Bezier (`C` 命令)：
```
M {startX} {startY} C {cp1x} {cp1y}, {cp2x} {cp2y}, {endX} {endY}
```

同行连接使用直线 (`L` 命令)。

---

## 7. 动画

### 7.1 关键帧定义

#### nodePulse（处理中节点脉冲）
```css
@keyframes nodePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(173, 199, 255, 0.4); }
  50%     { box-shadow: 0 0 20px 4px rgba(173, 199, 255, 0.15); }
}
.node-pulse { animation: nodePulse 2s ease-in-out infinite; }
```
用于：STT 监听节点、LLM 流式生成节点。

#### flowDash（数据流动画）
```css
@keyframes flowDash {
  to { stroke-dashoffset: -24; }
}
.flow-line {
  stroke-dasharray: 10 5;
  animation: flowDash 1.0s linear infinite;
}
```
用于：所有数据流 SVG 路径。

#### keywordPulse（关键词检测点）
```css
@keyframes keywordPulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50%     { opacity: 1;    transform: scale(1.3); }
}
.keyword-dot { animation: keywordPulse 1.5s ease-in-out infinite; }
```
用于：STT 监听节点标题旁的关键词检测指示灯。

#### loopFlow（循环回流动画）
```css
@keyframes loopFlow {
  0%   { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -24; }
}
.loop-line {
  stroke-dasharray: 6 6;
  animation: loopFlow 1s linear infinite;
}
```
用于：流程循环回路连接线。

#### portFlowPulse（活跃端口脉冲）
```css
@keyframes portFlowPulse {
  0%, 100% { box-shadow: 0 0 6px rgba(74, 142, 255, 0.5); }
  50%     { box-shadow: 0 0 18px rgba(74, 142, 255, 0.85); }
}
```
用于：数据流通中端口（`.io-port.flowing`）。

#### blink（流式文字光标）
```css
@keyframes blink {
  0%, 50%  { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.stream-cursor {
  animation: blink 0.8s step-end infinite;
  color: #4a8eff;
}
```
用于：LLM 流式输出中的光标字符 "█"。

### 7.2 过渡时间统一规范

| 作用域 | 属性 | 时长 | 缓动 |
|---|---|---|---|
| `.node-card` | transform, box-shadow, border-color | 0.2s | ease |
| `.tab-btn` | color | 0.2s | ease |
| `.io-port` | all | 0.2s | ease |
| `.io-label` | opacity | 0.15s | ease |
| `.node-card:hover` | transform, z-index | 0.2s | ease |
| `.chevron-icon` | transform (旋转) | 0.2s | ease |
| `.sidebar-section-content` | max-height (展开/折叠) | 0.25s | ease |
| `#canvas-content` | transform (缩放) | 0.2s | ease |
| `.flow-toggle-btn` | color, background | 0.2s | ease |
| `.detail-tab-btn` | color | 0.2s | ease |
| 状态栏链接 | opacity | 0.2s | ease |

### 7.3 Tailwind 内置动画

- `animate-pulse`：状态指示点、数据流通标识、"监听中..." 提示
- `active:scale-90`：按钮按下反馈

---

## 8. 布局组件

### 8.1 顶部导航栏

```
fixed top-0 left-0 w-full z-50
flex justify-between items-center px-6 h-14
bg-slate-950/80 backdrop-blur-xl
border-b border-outline-variant/50
```

内容：左侧 Logo + 版本号，右侧通知图标。

### 8.2 左侧边栏

```
fixed left-0 top-14 w-64 z-40
h-[calc(100vh-88px)]  (减去导航56px + 状态栏32px)
flex flex-col py-4
bg-slate-950/90 backdrop-blur-2xl
border-r border-outline-variant/50
overflow-y-auto
```

**手风琴结构：**
```
.sidebar-section
  > button (toggle header)
    > icon + text                     -- 左侧
    > chevron_right (Material Symbol) -- 右侧
  > .sidebar-section-content
    > 子项 buttons
```

**折叠动画：**
```css
.sidebar-section-content {
  overflow: hidden;
  transition: max-height 0.25s ease;
}
.sidebar-section-content.collapsed { max-height: 0 !important; }
```

**Chevron 旋转：**
```css
.chevron-icon { transition: transform 0.2s ease; }
.chevron-icon.collapsed { transform: rotate(0deg); }
.chevron-icon.expanded   { transform: rotate(90deg); }
```

**树形层级缩进：** 每级 `pl-6` 或 `pl-7`。

### 8.3 底部状态栏

```
fixed bottom-0 left-0 w-full z-50
flex justify-between items-center px-6 h-8
bg-slate-950
border-t border-outline-variant/50
font-inter text-[10px] uppercase tracking-widest
```

左侧：状态指示点 + 标签 + 值（最多 3 组，`gap-6`）。
右侧：链接（API 参考 / 文档 / 支持），`gap-4`。

### 8.4 右侧详情面板（#detail-panel）

```
fixed right-0 top-14 bottom-8 z-30
w-[320px] flex flex-col
bg-[#020617]  (slate-950, 不透明)
```

与主内容区无 margin——直接贴合。

**内部结构：**
```
Header    (p-4, border-b, flex, shrink-0)
  ├── icon + 节点名称
  └── close 按钮

Tab Bar   (flex, border-b, shrink-0)
  ├── 详情 (.detail-tab-btn)
  ├── 配置 (.detail-tab-btn)
  └── 日志 (.detail-tab-btn)

Content   (flex-1, overflow-y-auto)
  └── .detail-tab-content (×3)

Footer    (p-4, border-t, flex gap-2, shrink-0)
  ├── 取消 (bg-surface-variant)
  └── 保存配置 (bg-primary)
```

### 8.5 缩放控制栏

```
fixed z-50
left: 272px (sidebar 256px + 16px margin), bottom: 48px
flex items-center gap-1
p-1.5
bg-slate-950/80 backdrop-blur-md
border border-outline-variant/50 rounded-lg
```

**内容（从左到右）：**
1. 3 个流程视图切换按钮（全部 / 数据流 / 事件流）
2. 竖线分隔 `w-[1px] h-5 bg-outline-variant/50`
3. Zoom Out（-）
4. 百分比输入框（w-12, 透明背景, text-[12px] font-code-label text-primary）
5. Zoom In（+）
6. 竖线分隔
7. 适应屏幕

**缩放范围：** 25% ~ 300%

### 8.6 画布

```
flex-1 ml-64 relative
bg-[#121417]
overflow-auto
```

**网格背景：**
```css
background-image:
  linear-gradient(#31353d 1px, transparent 1px),
  linear-gradient(90deg, #31353d 1px, transparent 1px);
background-size: 32px 32px;
opacity: 0.15;
```

**尺寸：** 1700px × 1250px（可缩放，`transform-origin: 0 0`）。

**中键拖拽：** mouse button === 1 激活平移，cursor 变为 `grabbing`。

---

## 9. 流程视图切换

### 9.1 CSS 控制

Canvas 容器通过 `data-flow` 属性控制显示：

```css
.flow-view[data-flow="data"]  .event-only { display: none !important; }
.flow-view[data-flow="event"] .data-only  { display: none !important; }
```

### 9.2 class 分配规则

- I/O 端口 → `.data-only`（仅在"全部"和"数据流"显示）
- SVG 数据流线组 → `<g class="data-only">`
- SVG 事件流线组 → `<g class="event-only">`
- 节点内事件专属信息 → `.event-only`

---

## 10. 滚动条

```css
::-webkit-scrollbar             { width: 6px; }
::-webkit-scrollbar-track       { background: #10131b; }           /* surface */
::-webkit-scrollbar-thumb       { background: #31353d; border-radius: 3px; }  /* surface-variant */
::-webkit-scrollbar-thumb:hover { background: #414754; }           /* outline-variant */
```

---

## 11. 全局样式

### 11.1 Body

```css
body {
  font-family: 'Inter', sans-serif;
  background: #10131b;          /* background */
  color: #e0e2ed;               /* on-surface */
  font-size: 16px;              /* body-main */
  line-height: 1.6;
}
```

### 11.2 Selection

选中文字：背景 `#e94560`（红色强调），颜色白色。

### 11.3 全局 Card

```css
.glass-card {
  background: rgba(28, 32, 39, 0.85);
  backdrop-filter: blur(12px);
  border-radius: 8px;
  border: 1px solid rgba(65, 71, 84, 0.5);
}
```

---

## 12. 命名约定

### 12.1 CSS Class 命名

- `kebab-case`，功能描述优先
- 状态：`active` / `collapsed` / `expanded` / `disabled` / `panel-closed`
- 视图：`data-only` / `event-only`
- 组件：`node-card` / `glass-node` / `io-port` / `tab-btn` / `flow-toggle-btn` / `detail-tab-btn` / `workflow-badge` / `stream-cursor` / `keyword-dot`

### 12.2 HTML ID 命名

- `kebab-case`，语义化
- `detail-panel` / `canvas-content` / `canvas-container` / `connections-svg` / `zoom-input`
- Tab content: `tab-{node}-{section}` → `tab-stt`, `tab-stt-io`, `tab-stt-log`, `tab-stt-full`

### 12.3 图标

统一使用 [Material Symbols Outlined](https://fonts.google.com/icons)，通过 Google Fonts 加载：
```
https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1
```

使用方式：
```html
<span class="material-symbols-outlined" style="font-variation-settings:'FILL' 0;">icon_name</span>
```

FILL 值：0 = 线性，1 = 填充。

---

## 13. 实施检查清单

新组件开发时确认：

- [ ] 颜色必须使用 Tailwind token 或 CSS 变量，禁止裸色值
- [ ] 字体：正文用 Inter，标签/代码/时间戳用 Space Grotesk
- [ ] 字号遵循 9/10/11/12/13/14/16/18/24/32 阶梯
- [ ] 圆角：按钮 4px、卡片 8px、标签 9999px
- [ ] 过渡动画 ≤ 0.25s
- [ ] hover 态必须有视觉反馈（颜色变化或 translateY(-2px)）
- [ ] 可操作元素需要 `cursor: pointer`
- [ ] 数据流和事件流用不同 CSS class 分离（`.data-only` / `.event-only`）
- [ ] I/O 端口仅在数据流视图中显示
- [ ] 毛玻璃面板统一 `backdrop-filter: blur()`
- [ ] 滚动条统一样式
- [ ] 图标使用 Material Symbols Outlined
