# TeamSpeak AI 重构实现计划

> 目标：Pipeline 引擎 + 标准化节点 + WebSocket 实时推送
> 执行：按序号顺序执行，每步完成后 git commit

---

## 文件变更总览

| 操作 | 文件数 | 说明 |
|------|--------|------|
| DELETE | 8 个 | 无用的存根和旧代码 |
| MODIFY | 3 个 | 现有文件适配新架构 |
| CREATE | 30 个 | 新架构核心代码 |

---

## 第一步：清理无用文件

删除以下 8 个不再需要的文件：

| # | 文件 | 理由 |
|---|------|------|
| 1 | `backend/api/dependencies.py` | 空存根，从未使用 |
| 2 | `backend/api/routes/__init__.py` | 空文件 |
| 3 | `backend/api/routes/ws_client.py` | 被 `ws_pipeline.py` 取代 (EventBus + ClientSession 模式废弃) |
| 4 | `backend/api/routes/control.py` | 存根实现，硬编码状态，前端未调用 |
| 5 | `backend/services/event_bus.py` | 被 PipelineEngine 的 EventEmitter 取代 |
| 6 | `backend/services/session_manager.py` | 从未被任何模块引用 |
| 7 | `backend/core/audio/opus_codec.py` | 空存根，仅 1 行 |
| 8 | `backend/models/voice_message.py` | 定义未在任何地方被 import |

---

## 第二步：创建 Pipeline 核心层

### 2.1 Pipeline 定义模型

**`backend/core/pipeline/__init__.py`**

**`backend/core/pipeline/definition.py`**

```python
@dataclass
class NodeDefinition:
    id: str               # 节点 ID, 如 "stt_01"
    type: str             # 节点类型, 如 "stt" | "llm" | "tts" | "input" | "output"
    name: str             # 显示名称
    config: dict          # 节点配置
    input_from: str | None  # 上游节点 ID, None 代表手动触发
    next_on_complete: str | None  # 完成后自动触发下游节点

@dataclass
class PipelineDefinition:
    id: str               # 功能页 ID
    name: str             # 显示名称
    group: str            # 所属分组
    icon: str             # 图标
    nodes: list[NodeDefinition]  # 有序节点列表
```

### 2.2 NodeContext + NodeOutput + NodeState

**`backend/core/pipeline/context.py`**

```python
class NodeState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class NodeOutput:
    data: dict            # 输出数据, 作为下游节点的 inputs

@dataclass
class NodeContext:
    pipeline_id: str
    node_def: NodeDefinition
    inputs: dict          # 来自上游节点的 data
    state: NodeState
    execution_id: str     # 每次执行的唯一 ID
```

### 2.3 Node 注册表

**`backend/core/pipeline/registry.py`**

```python
class NodeRegistry:
    """节点类型注册表"""
    _registry: dict[str, type[BaseNode]] = {}

    @classmethod
    def register(cls, node_type: str):
        """装饰器: @register_node("stt")"""

    @classmethod
    def create(cls, node_type: str, config: dict) -> BaseNode:
        """工厂方法，根据类型创建节点实例"""
```

### 2.4 Pipeline Engine（核心编排引擎）

**`backend/core/pipeline/engine.py`**

```python
class PipelineEngine:
    """Pipeline 编排引擎"""

    _definitions: dict[str, PipelineDefinition]  # 从 YAML 加载的所有定义
    _instances: dict[str, PipelineInstance]       # 运行中的实例
    _registry: NodeRegistry                        # 节点注册表
    _ws_emitters: dict[str, list[WebSocket]]      # feature_id → WebSocket 列表

    def load_definitions(self, config_dir: str):
        """加载 config/pipelines/*.yaml"""

    def get_definitions(self) -> list[PipelineDefinition]:
        """供前端获取所有功能页配置"""

    def register_ws(self, feature_id: str, ws: WebSocket):
        """WebSocket 订阅功能页"""

    def unregister_ws(self, feature_id: str, ws: WebSocket):
        """取消订阅"""

    def start_pipeline(self, feature_id: str, initial_input: dict) -> str:
        """启动新的 Pipeline 执行，返回 execution_id"""

    async def execute_node(self, execution_id: str, node_id: str, user_input: dict = None):
        """执行指定节点（内部调度用）"""

    async def handle_node_action(self, ws_msg: dict):
        """处理前端 node_action 消息"""
```

**`backend/core/pipeline/instance.py`**

```python
@dataclass
class PipelineInstance:
    execution_id: str
    pipeline_def: PipelineDefinition
    node_states: dict[str, NodeInstance]
    status: str  # "running" | "completed" | "error"
    started_at: datetime

@dataclass
class NodeInstance:
    node_def: NodeDefinition
    status: NodeState
    output: NodeOutput | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

### 2.5 EventEmitter

**`backend/core/pipeline/emitter.py`**

```python
class EventEmitter:
    """向订阅了某个 feature 的所有 WebSocket 推送事件"""

    _feature_id: str
    _connections: dict[str, list[WebSocket]]  # 引用 PipelineEngine 的注册表

    async def emit_node_update(
        self, node_id: str, status: str, summary: str = "",
        progress: float | None = None, data: dict = None
    ):
        """推送 node_update 事件到前端"""

    async def emit_node_complete(
        self, node_id: str, output: NodeOutput
    ):
        """推送节点完成事件"""

    async def emit_node_error(
        self, node_id: str, error: str
    ):
        """推送节点错误事件"""

    async def emit_pipeline_complete(self):
        """推送 pipeline 完成事件"""
```

---

## 第三步：实现具体节点

每个节点继承 `BaseNode`，用 `@register_node()` 装饰器注册。

**`backend/core/nodes/__init__.py`** — 导入所有节点，确保注册

**`backend/core/nodes/base.py`**

```python
class BaseNode(ABC):
    node_type: str  # 子类覆盖

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        """执行节点逻辑"""
```

### 3.1 InputNode

**`backend/core/nodes/input_node.py`** — `type: "input"`

- 等待用户输入 (音频/文件/文本)
- 输出: `{ "file": bytes, "filename": str, "mime_type": str }`

### 3.2 STTNode

**`backend/core/nodes/stt_node.py`** — `type: "stt"`

- 输入: `{ "audio": bytes }` (来自上游 input_node 或 node_action)
- 逻辑: 调用 `core/stt/factory.create_stt()` 进行转写
- 流式推送: 边识别边推送 `node_update` 含 `partial_text`
- 输出: `{ "text": str }`

接收前端 `node_action` 的 `upload` 动作传递的音频数据。

### 3.3 LLMNode

**`backend/core/nodes/llm_node.py`** — `type: "llm"`

- 输入: `{ "text": str }` (来自上游 STT 节点)
- 逻辑: 调用 `core/llm/factory.create_llm()` 进行流式推理
- 流式推送: `node_update` 推送 `content_chunk` + `reasoning`
- 输出: `{ "response": str, "reasoning": str }`

接收前端 `node_action` 的 `input` 动作传递的用户文字输入（可选）。

### 3.4 TTSNode

**`backend/core/nodes/tts_node.py`** — `type: "tts"`

- 输入: `{ "text": str }` (来自上游 LLM 节点)
- 逻辑: 调用 `core/tts/factory.create_tts()` 合成语音
- 输出: `{ "audio": bytes, "format": str }`

### 3.5 TTOutputNode (TeamSpeak 回传)

**`backend/core/nodes/ts_output_node.py`** — `type: "ts_output"`

- 输入: `{ "audio": bytes }` (来自上游 TTS 节点)
- 逻辑: 通过 `ws_teamspeak.TeamSpeakWebSocket.send_voice_message()` 注入 TeamSpeak
- 输出: `{ "sent": bool }`

---

## 第四步：新建 WebSocket 端点

**`backend/api/routes/ws_pipeline.py`**

统一的 Pipeline WebSocket 端点，替换旧 `ws_client.py`：

```
端点: GET /ws/pipeline
```

### 前端 → 后端消息处理

```python
# 根据 msg["type"] 路由:
"subscribe"       → engine.register_ws(feature_id, ws)
"unsubscribe"     → engine.unregister_ws(feature_id, ws)
"get_config"      → ws.send_json(engine.get_definitions())
"node_action"     → engine.handle_node_action(msg["data"])
```

### 生命周期

```python
@router.websocket("/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    await websocket.accept()
    subscribed_features = set()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            if msg_type == "subscribe":
                fid = msg_data["feature_id"]
                engine.register_ws(fid, websocket)
                subscribed_features.add(fid)

            elif msg_type == "unsubscribe":
                fid = msg_data["feature_id"]
                engine.unregister_ws(fid, websocket)
                subscribed_features.discard(fid)

            elif msg_type == "get_config":
                await websocket.send_json({
                    "type": "feature_config",
                    "data": engine.get_definitions()
                })

            elif msg_type == "node_action":
                await engine.handle_node_action(msg_data)

    except WebSocketDisconnect:
        for fid in subscribed_features:
            engine.unregister_ws(fid, websocket)
```

### 后端 → 前端事件格式

| type | data |
|------|------|
| `feature_config` | `[PipelineDefinition, ...]` |
| `pipeline_start` | `{execution_id, feature_id}` |
| `node_update` | `{feature_id, node_id, status, summary, progress?, data?}` |
| `node_complete` | `{feature_id, node_id, output}` |
| `node_error` | `{feature_id, node_id, error}` |
| `pipeline_complete` | `{execution_id}` |

---

## 第五步：修改现有后端文件

### 5.1 修改 `backend/main.py`

```python
# 移除的 import:
# from api.routes import ws_client    ← DELETE
# from api.routes import control      ← DELETE

# 移除的路由注册:
# app.include_router(ws_client.router)   ← DELETE
# app.include_router(control.router)     ← DELETE

# 新增的路由:
from api.routes import ws_pipeline
app.include_router(ws_pipeline.router)

# 新增启动时初始化 PipelineEngine
from core.pipeline.engine import engine
engine.load_definitions("config/pipelines")
```

### 5.2 修改 `backend/api/routes/ws_teamspeak.py`

移除 STT 逻辑，保留底层 TeamSpeak 音频中继：

```
REMOVE:
  - STT 实例创建 (get_stt_instance)
  - AudioBuffer 全局变量
  - process_complete_audio()
  - receive_from_teamspeak() 中的音频缓冲 + STT 触发逻辑

KEEP:
  - TeamSpeakWebSocket 类（connect/disconnect/receive/send）
  - /ws/teamspeak 端点（纯中继，不做任何处理）
  - /teamspeak/status, /connect, /disconnect REST 端点
```

将来 TS 音频触发 pipeline，通过外部机制（如配置 `ts_input` 节点从 audio_buffer 取数据），不在 ws_teamspeak.py 里硬编码。

### 5.3 修改 `backend/config.py`

追加 pipeline 配置：

```python
# Pipeline
pipeline_config_dir: str = "config/pipelines"
```

---

## 第六步：创建 Pipeline 定义文件

**`backend/config/pipelines/voice_chat.yaml`**

```yaml
id: voice_chat
name: 语音对话
group: core_features
icon: 🎙️
nodes:
  - id: input_01
    type: input
    name: 语音输入
    config: { input_type: audio }
  - id: stt_01
    type: stt
    name: 语音识别
    config: { provider: sensevoice }
    input_from: input_01
  - id: llm_01
    type: llm
    name: AI 回复
    config:
      model: MiniMax-M2.7
      system_prompt: 你是一个 TeamSpeak 语音助手，请用中文简洁回复
    input_from: stt_01
  - id: tts_01
    type: tts
    name: 语音合成
    config: { provider: edge, voice: zh-CN-XiaoxiaoNeural }
    input_from: llm_01
  - id: output_01
    type: ts_output
    name: TeamSpeak 播放
    config: {}
    input_from: tts_01
```

**`backend/config/pipelines/arena.yaml`** 和 **`backend/config/pipelines/darkzone.yaml`** 类似。

---

## 第七步：前端改造

### 7.1 新增前端文件

```
src/
├── api/
│   └── pipeline.js          # Pipeline WebSocket 客户端 (取代旧 websocket.js)
├── stores/
│   ├── pipeline.js           # Pipeline 状态管理 (取代 conversation.js + app.js 部分功能)
│   └── sidebar.js            # 侧边栏动态配置 (新增)
├── components/
│   ├── pipeline/
│   │   ├── PipelineView.vue        # 横向流程图
│   │   ├── PipelineNode.vue         # 单个节点
│   │   └── PipelineEdge.vue         # 连接线
│   ├── panels/
│   │   ├── DynamicPanel.vue         # 动态面板
│   │   └── ImportantPanel.vue       # 重要信息区
│   ├── display/                     # 展示类组件
│   │   ├── TextDisplay.vue
│   │   ├── StreamingText.vue
│   │   └── AudioPlayer.vue
│   └── action/                      # 操作类组件
│       ├── AudioFileUploader.vue    # 音频上传
│       ├── ImageFileUploader.vue    # 图片上传
│       ├── TextInput.vue
│       └── ErrorDisplay.vue
└── views/
    └── FeaturePage.vue              # 功能页容器
```

### 7.2 修改现有前端文件

**`src/main.js`** — 新增 store 注册，原有不变

**`src/App.vue`** — 简化，只包含 AppLayout

**`components/layout/AppLayout.vue`** — 整体重写：
- Header: 标题 + 连接状态
- Sidebar: 从 `sidebar.js` store 渲染动态菜单
- Content: `FeaturePage.vue` (含 PipelineView + DynamicPanel + ImportantPanel)
- Footer: 日志控制台（保留）

### 7.3 保留的旧文件

- `src/components/common/StatusIndicator.vue` — 保持，Header 需要
- `src/api/files.js` — 保持，文件 API 仍有用
- `src/stores/files.js` — 保持，文件存储仍有用

### 7.4 删除的前端文件

- `src/stores/app.js` — 功能移入 pipeline.js + sidebar.js
- `src/stores/conversation.js` — 功能移入 pipeline.js
- `src/api/websocket.js` — 被 api/pipeline.js 取代
- `src/components/common/FileUploader.vue` — 被 action/* 组件取代

---

## 第八步：按顺序执行

```
Step 1:  清理后端无用文件 (DELETE 8 个)
Step 2:  创建 Pipeline 核心层 (definition, context, registry, engine, emitter)
Step 3:  实现具体节点 (input, stt, llm, tts, ts_output)
Step 4:  创建 ws_pipeline.py WebSocket 端点
Step 5:  修改 main.py, ws_teamspeak.py, config.py
Step 6:  创建 YAML Pipeline 定义文件
Step 7:  前端改造 (新增 15 个文件, 修改 4 个, 删除 4 个)
Step 8:  集成测试
```

每个 Step 完成后 git commit，确保可回滚。
