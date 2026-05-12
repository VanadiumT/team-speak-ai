# 流程变量系统与开始节点设计

> 定义流程参数机制、系统变量机制、以及 start / flow_var_read / flow_var_write / sys_var_read / sys_var_write 五个新节点的完整设计。

---

## 1. 两套变量系统总览

| | 流程参数 (Flow Parameters) | 系统变量 (System Variables) |
|---|---|---|
| 作用域 | 单个流程 | 全局跨流程 |
| 生命周期 | 每次执行重置（可被 Start 节点初始化） | 持久化到磁盘，跨流程共享 |
| 管理入口 | 前端流程参数面板 | 前端系统设置面板 |
| 读写节点 | `flow_var_read` / `flow_var_write` | `sys_var_read` / `sys_var_write` |
| 存储位置 | 流程 JSON 的 `params` 字段 | `backend/data/system_vars.json` |
| $param.xxx | 保留，用于 IO 端口配置的模板解析 | 不适用 |

### 1.1 流程参数存储结构

流程 JSON 中新增 `params` 字段：

```json
{
  "id": "darkzone",
  "name": "暗区竞标赛",
  "params": {
    "skill_prompt": "你是暗区竞标赛的AI助手...",
    "max_history": 20,
    "default_voice": "zh-CN-YunxiNeural"
  },
  "nodes": [...],
  "connections": [...]
}
```

### 1.2 系统变量存储结构

`backend/data/system_vars.json`：

```json
{
  "vars": {
    "global_model": "gpt-4-turbo",
    "default_language": "zh",
    "api_key_minimax": "..."
  },
  "updated_at": "2026-05-09T12:00:00Z"
}
```

### 1.3 $param.xxx 保留机制

在节点配置字段和 IO 端口默认值中，支持 `$param.xxx` 模板替换：

```
节点配置: { "prompt": "$param.skill_prompt" }
→ 执行时替换为 flow.params["skill_prompt"] 的值
```

这是底层能力，正常用户不直接使用。主要用于：
- IO 端口配置的默认值模板
- 高级用户在配置字段中做动态引用

---

## 2. Start 节点 — `start`

### 2.1 基本信息

| 字段 | 值 |
|---|---|
| type | `start` |
| name | `开始` |
| icon | `play_arrow` |
| color | `secondary`（绿色） |
| 类别 | Source |
| 执行模式 | One-shot（流程启动时自动执行） |
| 写 accumulated_context | 可选（写入流程参数） |

### 2.2 端口

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 出 | `event-out` | `event` | always | 流程启动信号，触发下游 |
| 出 | `data-out` | `any` | on-demand | 携带初始数据（可选） |

无输入端口 — 它是一切的起点。

### 2.3 配置

```json
{
  "auto_run": true,
  "init_params": {}
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `auto_run` | boolean | `true` | 流程启动时是否自动执行。`false` 则等待手动触发 |
| `init_params` | object | `{}` | 启动时写入流程参数的 key-value 对 |

### 2.4 标签页

| tab id | label | 内容 |
|---|---|---|
| `config` | 配置 | `auto_run` 开关 + `init_params` 键值对编辑器 |
| `detail` | 详情 | 启动状态：等待启动 / 已触发 / 触发时间 |
| `io-data` | IO数据 | 输出端口的数据快照（init_params 内容） |
| `log` | 日志 | 启动日志 |

### 2.5 执行逻辑

```
execute(context, emit):
    1. emit.node_status_changed("processing")
    2. 读取 context.node_config["init_params"]
    3. 如果 init_params 非空:
         遍历 key-value，写入 context.accumulated_context[key] = value
         同时写入流程参数（通过 FlowManager 更新 flow.params）
    4. emit.node_log_entry("info", f"流程启动，写入 {len(init_params)} 个参数")
    5. return NodeOutput(data={"params": init_params}, trigger_next=True)
```

### 2.6 引擎改动

`PipelineEngine.start_pipeline` 的启动逻辑变更：

```
当前：
  start_pipeline → 找 listener 节点 → 启动后台 Task

新增：
  start_pipeline → 找所有 type=="start" 且 auto_run==true 的节点
               → 并行执行 execute_node（各自触发下游）
               → 同时找 listener 节点 → 启动后台 Task（不变）
```

### 2.7 前端展示

**Flow Mode body：**
- `pending` → "等待启动..."（auto_run=false 时）
- `processing` → "流程已启动" + 脉冲动画
- `completed` → "✓ 已触发" + 触发时间 + 写入的参数列表

**Edit Mode body：**
- config tab → `auto_run` 开关 + `init_params` 可编辑键值对表格
- detail tab → 同 Flow Mode

**卡片样式：** 左侧无端口，右侧一个绿色圆点（event-out）+ 可选蓝色方块（data-out，any 类型端口渲染为方块？或保持圆形用颜色区分）。

---

## 3. 流程参数读取节点 — `flow_var_read`

### 3.1 基本信息

| 字段 | 值 |
|---|---|
| type | `flow_var_read` |
| name | `读取流程参数` |
| icon | `input` |
| color | `primary`（蓝色） |
| 类别 | Transform |
| 执行模式 | One-shot |
| 写 accumulated_context | 否 |

### 3.2 端口

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `trigger-in` | `event` | on-demand | 手动触发读取 |
| 出 | `data-out` | `any` | always | 读取到的值 |
| 出 | `done` | `event` | on-demand | 读取完成信号 |

### 3.3 配置

```json
{
  "key": "skill_prompt",
  "default_value": ""
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `key` | string | `""` | 要读取的流程参数 key |
| `default_value` | string | `""` | key 不存在时的默认值 |

### 3.4 标签页

| tab id | label | 内容 |
|---|---|---|
| `config` | 配置 | key 输入框 + default_value 输入框 |
| `detail` | 详情 | 当前读取到的值预览（实时） |
| `io-data` | IO数据 | data-out 端口的值快照 |
| `io-mgmt` | IO管理 | 端口可见性管理 |
| `log` | 日志 | 读取日志 |

### 3.5 执行逻辑

```
execute(context, emit):
    1. emit.node_status_changed("processing")
    2. key = context.node_config["key"]
    3. default = context.node_config.get("default_value", "")
    4. value = context.accumulated_context.get(key, default)
       （流程参数在 start 节点执行时已写入 accumulated_context）
    5. emit.node_log_entry("info", f"读取流程参数 {key} = {value}")
    6. return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
```

### 3.6 前端展示

**Flow Mode body：**
- `pending` → "等待触发..."
- `processing` → spinner
- `completed` → key = value 的预览，格式化显示

**Edit Mode body：**
- config tab → key 输入框（带自动补全：列出当前流程已有的 params keys）+ default_value 输入框
- detail tab → 当前值实时预览

---

## 4. 流程参数写入节点 — `flow_var_write`

### 4.1 基本信息

| 字段 | 值 |
|---|---|
| type | `flow_var_write` |
| name | `写入流程参数` |
| icon | `output` |
| color | `primary`（蓝色） |
| 类别 | Transform |
| 执行模式 | One-shot |
| 写 accumulated_context | 是（指定 key） |

### 4.2 端口

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `data-in` | `any` | always | 待写入的值 |
| 入 | `trigger-in` | `event` | on-demand | 触发写入 |
| 出 | `data-out` | `any` | always | 写入后的值（透传） |
| 出 | `done` | `event` | on-demand | 写入完成信号 |

### 4.3 配置

```json
{
  "key": "llm_response",
  "merge_mode": "overwrite"
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `key` | string | `""` | 要写入的流程参数 key |
| `merge_mode` | string | `"overwrite"` | `overwrite`（覆盖）/ `append`（追加到列表） |

### 4.4 标签页

| tab id | label | 内容 |
|---|---|---|
| `config` | 配置 | key 输入框 + merge_mode 下拉选择 |
| `detail` | 详情 | 最近一次写入的 key = value 预览 |
| `io-data` | IO数据 | data-in（输入值）和 data-out（透传值）快照 |
| `io-mgmt` | IO管理 | 端口可见性管理 |
| `log` | 日志 | 写入日志 |

### 4.5 执行逻辑

```
execute(context, emit):
    1. emit.node_status_changed("processing")
    2. key = context.node_config["key"]
    3. merge_mode = context.node_config.get("merge_mode", "overwrite")
    4. value = context.inputs.get("data")   # 从输入端口读取
    5. 如果 merge_mode == "append":
         existing = context.accumulated_context.get(key, [])
         if not isinstance(existing, list): existing = [existing]
         existing.append(value)
         context.accumulated_context[key] = existing
       否则:
         context.accumulated_context[key] = value
    6. emit.node_log_entry("info", f"写入流程参数 {key} = {value}")
    7. return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
```

### 4.6 前端展示

**Flow Mode body：**
- `pending` → "等待输入..."
- `processing` → spinner
- `completed` → "✓ 已写入 key = value"

**Edit Mode body：**
- config tab → key 输入框 + merge_mode 下拉
- detail tab → 最近写入预览

---

## 5. 系统变量读取节点 — `sys_var_read`

### 5.1 基本信息

| 字段 | 值 |
|---|---|
| type | `sys_var_read` |
| name | `读取系统变量` |
| icon | `settings_input` |
| color | `tertiary`（橙色） |
| 类别 | Transform |
| 执行模式 | One-shot |
| 写 accumulated_context | 否 |

### 5.2 端口

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `trigger-in` | `event` | on-demand | 手动触发 |
| 出 | `data-out` | `any` | always | 读取到的值 |
| 出 | `done` | `event` | on-demand | 完成信号 |

### 5.3 配置

```json
{
  "key": "global_model",
  "default_value": ""
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `key` | string | `""` | 要读取的系统变量 key |
| `default_value` | string | `""` | key 不存在时的默认值 |

### 5.4 标签页

| tab id | label | 内容 |
|---|---|---|
| `config` | 配置 | key 输入框 + default_value 输入框 |
| `detail` | 详情 | 当前读取到的值预览 |
| `io-data` | IO数据 | data-out 快照 |
| `io-mgmt` | IO管理 | 端口可见性管理 |
| `log` | 日志 | 读取日志 |

### 5.5 执行逻辑

```
execute(context, emit):
    1. emit.node_status_changed("processing")
    2. key = context.node_config["key"]
    3. default = context.node_config.get("default_value", "")
    4. value = sys_var_manager.get(key, default)
       （从 data/system_vars.json 读取，磁盘 IO）
    5. emit.node_log_entry("info", f"读取系统变量 {key} = {value}")
    6. return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
```

### 5.6 前端展示

**Flow Mode body：**
- `pending` → "等待触发..."
- `processing` → spinner
- `completed` → key = value 预览

**Edit Mode body：**
- config tab → key 输入框（带自动补全：列出已有系统变量 keys）+ default_value

---

## 6. 系统变量写入节点 — `sys_var_write`

### 6.1 基本信息

| 字段 | 值 |
|---|---|
| type | `sys_var_write` |
| name | `写入系统变量` |
| icon | `settings_output` |
| color | `tertiary`（橙色） |
| 类别 | Transform |
| 执行模式 | One-shot |
| 写 accumulated_context | 否 |

### 6.2 端口

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `data-in` | `any` | always | 待写入的值 |
| 入 | `trigger-in` | `event` | on-demand | 触发写入 |
| 出 | `data-out` | `any` | always | 写入后的值（透传） |
| 出 | `done` | `event` | on-demand | 完成信号 |

### 6.3 配置

```json
{
  "key": "last_response",
  "merge_mode": "overwrite"
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `key` | string | `""` | 要写入的系统变量 key |
| `merge_mode` | string | `"overwrite"` | `overwrite` / `append` |

### 6.4 标签页

| tab id | label | 内容 |
|---|---|---|
| `config` | 配置 | key 输入框 + merge_mode 下拉 |
| `detail` | 详情 | 最近写入预览 |
| `io-data` | IO数据 | data-in / data-out 快照 |
| `io-mgmt` | IO管理 | 端口可见性管理 |
| `log` | 日志 | 写入日志 |

### 6.5 执行逻辑

```
execute(context, emit):
    1. emit.node_status_changed("processing")
    2. key = context.node_config["key"]
    3. merge_mode = context.node_config.get("merge_mode", "overwrite")
    4. value = context.inputs.get("data")
    5. sys_var_manager.set(key, value, merge_mode)
       （写入 data/system_vars.json，磁盘 IO）
    6. emit.node_log_entry("info", f"写入系统变量 {key} = {value}")
    7. return NodeOutput(data={"value": value, "key": key}, trigger_next=True)
```

### 6.6 前端展示

同 `sys_var_read`，但 detail tab 显示"已写入 key = value"。

---

## 7. 流程参数管理面板（前端 UI）

### 7.1 入口位置

**不是独立的侧栏 section。** 流程参数面板嵌入在右侧详情面板中，或作为流程编辑模式下的一个专用 tab。

当用户选中一个流程并进入编辑模式后，在右侧面板或画布上方的工具栏中出现"流程参数"入口按钮。点击后展开参数编辑面板。

仅在编辑模式下可见（Flow Mode 下不显示）。

### 7.2 面板结构

```
┌─────────────────────────────┐
│ 流程参数                    │
├─────────────────────────────┤
│ + 添加参数                  │
│                             │
│ skill_prompt    [你是AI...] │
│ max_history     [20       ] │
│ default_voice   [zh-CN...] │
│                             │
│ [保存]                      │
└─────────────────────────────┘
```

### 7.3 功能

- **列表展示：** 显示当前流程的所有参数（key / value）
- **新建：** 点击"+添加参数"，输入 key 和 value
- **编辑：** 点击某行，内联编辑 value
- **删除：** 点击行尾删除图标，确认后删除
- **保存：** 点击"保存"按钮，通过 `flow.update` 命令更新 `flow.params`

### 7.4 WS 命令

利用已有的 `flow.update` 命令扩展：

```
前端发送:
{
  "action": "flow.update",
  "flow_id": "darkzone",
  "params": {
    "params": {
      "skill_prompt": "你是AI助手...",
      "max_history": 20
    }
  }
}

后端处理:
→ FlowManager.update_flow_params(flow_id, params)
→ 更新流程 JSON 的 params 字段
→ 广播 flow.params_updated 事件给其他订阅者
```

### 7.5 新增 WS 事件

| action | 方向 | params | 说明 |
|---|---|---|---|
| `flow.params_updated` | S→C | `{flow_id, params}` | 参数变更广播 |

### 7.6 涉及文件

| 文件 | 操作 |
|---|---|
| `components/pipeline/FlowParamsPanel.vue` | 新建：参数编辑面板组件 |
| `stores/editor.js` | 修改：添加 `flowParams` 状态和 `updateFlowParams` action |
| `components/layout/AppLayout.vue` | 修改：在编辑模式下显示流程参数入口 |

---

## 8. 系统变量管理面板（前端 UI）

### 8.1 入口位置

**侧栏新增第三个 section：`sys_vars`（系统变量）**，位于"工作流"和"系统设置"之间。

当前侧栏结构：
```
工作流 (workflows)
  └── 流程树...
系统设置 (system_settings)     ← 现有
  └── OCR设置 / LLM设置 / ...
```

新增后：
```
工作流 (workflows)
  └── 流程树...
系统变量 (sys_vars)            ← 新增
  └── 变量列表（内联编辑）
系统设置 (system_settings)
  └── OCR设置 / LLM设置 / ...
```

所有模式下可见（不需要选中流程）。

### 8.2 面板结构

```
▼ 系统变量                          [+] [刷新]
  global_model        gpt-4-turbo   [✎] [×]
  default_language    zh            [✎] [×]
  api_key_minimax     sk-***        [✎] [×]
```

展开后直接在侧栏内显示变量列表，每行：key + value（截断显示）+ 编辑/删除按钮。

点击编辑 → 内联编辑 value，失焦或回车自动保存。
点击删除 → 确认后删除。
点击 [+] → 新增一行，输入 key 和 value。

### 8.3 功能

- **列表展示：** 显示所有系统变量（key / value，长值截断）
- **新建：** 点击"+"按钮，新增一行输入 key 和 value
- **编辑：** 点击编辑图标，value 变为输入框，失焦自动保存
- **删除：** 点击删除图标，确认后删除
- **刷新：** 点击刷新按钮，重新从后端拉取
- **自动同步：** 连接时自动拉取，其他客户端修改时实时更新

### 8.4 WS 命令

| action | 方向 | params | 说明 |
|---|---|---|---|
| `sys_var.list` | C→S | `{}` | 列出所有系统变量 |
| `sys_var.get` | C→S | `{key}` | 获取单个变量 |
| `sys_var.set` | C→S | `{key, value}` | 设置变量 |
| `sys_var.delete` | C→S | `{key}` | 删除变量 |
| `sys_var.list_result` | S→C | `{vars: {k:v}}` | 列表结果 |
| `sys_var.updated` | S→C | `{key, value}` | 变更广播 |

### 8.5 侧栏树生成改动

后端 `FlowManager.build_sidebar_tree()` 新增 `sys_vars` section：

```python
# 现有:
SidebarNode(id="workflows", ...)
SidebarNode(id="system_settings", ...)

# 新增（插入到 workflows 和 system_settings 之间）:
SidebarNode(id="workflows", ...)
SidebarNode(
    id="sys_vars", name="系统变量", icon="data_object", type="section",
    children=[
        # children 为空，前端渲染时用 SysVarsPanel 组件替代递归树
    ]
)
SidebarNode(id="system_settings", ...)
```

### 8.6 前端渲染逻辑

`AppLayout.vue` 的侧栏渲染中，对 `sys_vars` section 做特殊处理：

```vue
<template v-for="section in sidebarTree" :key="section.id">
  <!-- 系统变量 section：用 SysVarsPanel 替代递归树 -->
  <div v-if="section.id === 'sys_vars'" class="sb-section">
    <div class="sb-section-row">
      <button class="sb-section-btn" @click="toggleSection('sys_vars')">
        <span class="material-symbols-outlined sb-section-icon">data_object</span>
        <span class="sb-section-name">系统变量</span>
        <span class="material-symbols-outlined sb-chevron" ...>chevron_right</span>
      </button>
    </div>
    <SysVarsPanel v-if="isExpanded('sys_vars')" />
  </div>

  <!-- 其他 section：正常递归渲染 -->
  <div v-else class="sb-section">
    ...
  </div>
</template>
```

### 8.7 涉及文件

| 文件 | 操作 |
|---|---|
| `components/layout/SysVarsPanel.vue` | 新建：系统变量面板组件 |
| `stores/sysvars.js` | 新建：系统变量 store（list/get/set/delete + WS 事件） |
| `components/layout/AppLayout.vue` | 修改：sys_vars section 特殊渲染 |
| `backend/core/flow/manager.py` | 修改：`build_sidebar_tree()` 添加 sys_vars section |
| `backend/api/routes/ws_main.py` | 修改：添加 sys_var.list/get/set/delete 命令 |
| `backend/main.py` | 修改：初始化 SysVarManager |

---

## 9. 后端新增模块

### 9.1 `core/variables/manager.py` — SysVarManager

```
class SysVarManager:
    def __init__(data_dir)
    def get(key, default=None) -> any
    def set(key, value, merge_mode="overwrite")
    def delete(key)
    def list_all() -> dict
    def _load()  # 从 system_vars.json 读取
    def _save()  # 写入 system_vars.json
```

### 9.2 `core/nodes/start_node.py`

注册 `@NodeRegistry.register("start")`

### 9.3 `core/nodes/flow_var_read_node.py`

注册 `@NodeRegistry.register("flow_var_read")`

### 9.4 `core/nodes/flow_var_write_node.py`

注册 `@NodeRegistry.register("flow_var_write")`

### 9.5 `core/nodes/sys_var_read_node.py`

注册 `@NodeRegistry.register("sys_var_read")`

### 9.6 `core/nodes/sys_var_write_node.py`

注册 `@NodeRegistry.register("sys_var_write")`

### 9.7 `core/nodes/__init__.py`

新增 import 6 个模块。

### 9.8 `core/pipeline/registry.py` — `_build_metadata()`

新增 6 个 `NodeTypeDef` 条目。

### 9.9 `core/flow/manager.py`

新增 `update_flow_params(flow_id, params)` 方法。

### 9.10 `api/routes/ws_main.py`

- `flow.update` 命令支持 `params` 字段
- 新增 `sys_var.list` / `sys_var.get` / `sys_var.set` / `sys_var.delete` 命令处理
- 连接时推送系统变量列表（可选）

### 9.11 `main.py`

初始化 `SysVarManager`。

---

## 10. 前端新增/修改文件

| 文件 | 操作 | 阶段 |
|---|---|---|
| `components/pipeline/nodes/StartNode.vue` | 新建 | 2 |
| `components/pipeline/nodes/FlowVarReadNode.vue` | 新建 | 3 |
| `components/pipeline/nodes/FlowVarWriteNode.vue` | 新建 | 3 |
| `components/pipeline/nodes/SysVarReadNode.vue` | 新建 | 4 |
| `components/pipeline/nodes/SysVarWriteNode.vue` | 新建 | 4 |
| `components/pipeline/nodes/registry.js` | 添加 5 个映射 | 2-4 |
| `components/pipeline/FlowParamsPanel.vue` | 新建：流程参数编辑面板（编辑模式下显示） | 1 |
| `components/layout/SysVarsPanel.vue` | 新建：系统变量面板（侧栏 sys_vars section 内） | 4 |
| `components/layout/AppLayout.vue` | 修改：sys_vars section 特殊渲染 + 流程参数入口 | 1, 4 |
| `stores/editor.js` | 修改：支持 flowMeta.params 读写 | 1 |
| `stores/sysvars.js` | 新建：系统变量 store | 4 |

## 11. 后端新增/修改文件

| 文件 | 操作 | 阶段 |
|---|---|---|
| `core/nodes/start_node.py` | 新建 | 2 |
| `core/nodes/flow_var_read_node.py` | 新建 | 3 |
| `core/nodes/flow_var_write_node.py` | 新建 | 3 |
| `core/nodes/sys_var_read_node.py` | 新建 | 4 |
| `core/nodes/sys_var_write_node.py` | 新建 | 4 |
| `core/nodes/__init__.py` | 添加 6 个 import | 2-4 |
| `core/pipeline/registry.py` | `_build_metadata()` 添加 6 个 NodeTypeDef | 2-4 |
| `core/pipeline/engine.py` | 修改启动逻辑（找 start 节点并行执行） | 2 |
| `core/flow/manager.py` | 添加 `update_flow_params` + `build_sidebar_tree` 新增 sys_vars section | 1, 4 |
| `core/variables/manager.py` | 新建：SysVarManager | 4 |
| `api/routes/ws_main.py` | flow.update 支持 params + sys_var 命令 | 1, 4 |
| `main.py` | 初始化 SysVarManager | 4 |

---

## 12. 实施计划

### 阶段 1：流程参数基础设施
1. `FlowManager` 新增 `update_flow_params(flow_id, params)`
2. `ws_main.py` 的 `flow.update` 命令支持 `params` 字段
3. `editor.js` store 添加 `flowParams` 状态和 `updateFlowParams` action
4. `FlowParamsPanel.vue` 前端面板（编辑模式下显示，内联编辑 key-value）
5. `AppLayout.vue` 添加流程参数入口按钮

### 阶段 2：Start 节点
1. `start_node.py` 实现（auto_run + init_params 写入 accumulated_context）
2. `_build_metadata()` 添加 start 的 NodeTypeDef
3. `StartNode.vue` 前端组件
4. `registry.js` 添加映射
5. `engine.py` 启动逻辑修改：找所有 `type=="start"` 且 `auto_run==true` 的节点并行执行

### 阶段 3：流程参数读写节点
1. `flow_var_read_node.py` / `flow_var_write_node.py` 实现
2. `_build_metadata()` 添加两个 NodeTypeDef
3. `FlowVarReadNode.vue` / `FlowVarWriteNode.vue` 前端组件
4. `registry.js` 添加映射

### 阶段 4：系统变量
1. `core/variables/manager.py` — SysVarManager 实现（JSON 持久化）
2. `main.py` 初始化 SysVarManager
3. `ws_main.py` 添加 `sys_var.list` / `sys_var.get` / `sys_var.set` / `sys_var.delete` 命令
4. `core/flow/manager.py` — `build_sidebar_tree()` 添加 `sys_vars` section（workflows 和 system_settings 之间）
5. `sys_var_read_node.py` / `sys_var_write_node.py` 实现
6. `_build_metadata()` 添加两个 NodeTypeDef
7. `SysVarReadNode.vue` / `SysVarWriteNode.vue` 前端组件
8. `SysVarsPanel.vue` — 侧栏内系统变量面板（内联编辑 key-value）
9. `stores/sysvars.js` — 系统变量 store（WS 事件 + CRUD）
10. `AppLayout.vue` — sys_vars section 特殊渲染（用 SysVarsPanel 替代递归树）
