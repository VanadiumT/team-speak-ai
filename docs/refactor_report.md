# TeamSpeak AI 重构实现报告

> 目标：Pipeline 引擎 + 标准化节点 + WebSocket 实时推送
> 状态：✅ 已完成
> 日期：2026-04-24

---

## 实际文件变更统计

| 操作 | 个数 | 明细 |
|------|------|------|
| DELETE | 12 | 8 后端 + 4 前端无用的旧文件 |
| MODIFY | 6 | main.py, ws_teamspeak.py, config.py, App.vue, AppLayout.vue, pyproject.toml |
| CREATE | 26 | 新架构核心代码 |

---

## 完成步骤

### Step 1 ✅ 清理无用后端文件 (8 个)

| 文件 | 理由 |
|------|------|
| `backend/api/dependencies.py` | 空存根 |
| `backend/api/routes/__init__.py` | 空文件 |
| `backend/api/routes/ws_client.py` | 被 ws_pipeline.py 取代 |
| `backend/api/routes/control.py` | 存根，前端未调用 |
| `backend/services/event_bus.py` | 被 PipelineEngine EventEmitter 取代 |
| `backend/services/session_manager.py` | 从未被引用 |
| `backend/core/audio/opus_codec.py` | 空存根 |
| `backend/models/voice_message.py` | 从未被 import |

### Step 2 ✅ Pipeline 核心层 (6 文件)

| 文件 | 职责 |
|------|------|
| `backend/core/pipeline/definition.py` | Pipeline/Node 定义模型，支持 listener/trigger/input_mapping |
| `backend/core/pipeline/context.py` | NodeContext, NodeOutput, NodeState, NodeRuntime |
| `backend/core/pipeline/registry.py` | @register_node 装饰器 + 工厂 |
| `backend/core/pipeline/engine.py` | PipelineEngine: 编排引擎 + WS订阅 + 实例管理 |
| `backend/core/pipeline/emitter.py` | EventEmitter: WebSocket 实时推送 |
| `backend/core/audio/audio_bus.py` | 音频发布/订阅总线 |

### Step 3 ✅ 7 个具体节点

| 节点 | 类型 | 说明 |
|------|------|------|
| `input_image` | 输入 | 接收前端上传的图片 |
| `ocr` | 处理 | 图片文字识别（占位实现，可接 PaddleOCR） |
| `stt_listen` | **监听** | 常驻后台，AudioBus→STT→关键词检测→触发下游 |
| `context_build` | 处理 | 合并 OCR 文本 + STT 历史 + Skill 提示词为 LLM 上下文 |
| `llm` | 处理 | 流式调用 MiniMax（OpenAI 兼容），实时推送 content+reasoning |
| `tts` | 处理 | 调用 Edge/MiniMax TTS 合成音频 |
| `ts_output` | 输出 | 通过 ws_teamspeak 发送到 TeamSpeak 频道播放 |

所有节点通过 `@NodeRegistry.register("type")` 注册，引擎按需创建。

### Step 4 ✅ Pipeline WebSocket 端点

**`backend/api/routes/ws_pipeline.py`**

端点: `GET /ws/pipeline`

| 前端→后端 | 说明 |
|-----------|------|
| `subscribe` | 订阅功能页事件 |
| `unsubscribe` | 取消订阅 |
| `get_config` | 获取所有 Pipeline 定义 |
| `node_action` | 触发节点操作 (upload/trigger/restart/input_text) |

| 后端→前端 | 说明 |
|-----------|------|
| `feature_config` | Pipeline 定义列表 |
| `pipeline_start` / `pipeline_complete` | Pipeline 生命周期 |
| `node_update` | 节点进度/流式数据推送 |
| `node_complete` | 节点完成 |
| `node_error` | 节点错误 |
| `important_update` | 重要事件推送 |
| `pipeline_state` | 重连后恢复状态 |

### Step 5 ✅ 修改现有后端 (3 文件)

| 文件 | 变更 |
|------|------|
| `backend/main.py` | 移除旧路由 (ws_client, control)，添加 ws_pipeline，启动时加载 Pipeline 定义 |
| `backend/api/routes/ws_teamspeak.py` | 移除 STT 逻辑，精简为纯中继 + AudioBus 发布 |
| `backend/config.py` | 添加 `pipeline_config_dir` 配置项 |

### Step 6 ✅ Pipeline 定义 YAML

**`backend/config/pipelines/darkzone_championship.yaml`**

暗区锦标赛 Pipeline 定义，7 个节点，其中 `stt_listen_01` 为常驻监听节点，
其余为一次性 action 节点。触发链：

```
image_input → ocr_01 ─┐
                         ├→ context_01 → llm_01 → tts_01 → ts_output_01
stt_listen_01(关键词) ──┘
```

### Step 7 ✅ 前端改造

**删除 (4 个)**
- `frontend/src/stores/app.js` → 功能移入 pipeline.js + sidebar.js
- `frontend/src/stores/conversation.js` → 功能移入 pipeline.js
- `frontend/src/api/websocket.js` → 被 api/pipeline.js 取代
- `frontend/src/components/common/FileUploader.vue` → 被 action/* 取代

**新增 (13 个)**
| 文件 | 类型 | 职责 |
|------|------|------|
| `api/pipeline.js` | API | PipelineSocket WebSocket 客户端 |
| `stores/pipeline.js` | Store | Pipeline 节点状态管理 |
| `stores/sidebar.js` | Store | 侧边栏动态配置 |
| `pipeline/PipelineView.vue` | 组件 | 横向流程图 |
| `pipeline/PipelineNode.vue` | 组件 | 单个节点（状态灯/摘要） |
| `panels/DynamicPanel.vue` | 组件 | 根据节点类型+状态动态渲染 |
| `panels/ImportantPanel.vue` | 组件 | 重要事件列表 |
| `display/TextDisplay.vue` | 展示 | 文本+思考过程 |
| `display/StreamingText.vue` | 展示 | 流式文本（光标闪烁） |
| `display/AudioPlayer.vue` | 展示 | 音频信息 |
| `action/AudioFileUploader.vue` | 操作 | 拖拽/点击上传 |
| `action/ErrorDisplay.vue` | 操作 | 错误信息展示 |
| `views/FeaturePage.vue` | 页面 | 功能页面容器 |

**修改 (4 个)**
- `frontend/src/App.vue` — 简化，移除 initWebSocket
- `frontend/src/components/layout/AppLayout.vue` — 完整重写，动态侧边栏 + Pipeline 事件监听
- `frontend/src/main.js` — 无变动（Pinia 已注册）
- `frontend/src/components/common/StatusIndicator.vue` — 保留

---

## 暗区锦标赛完整流程

```
用户操作                         后端 Pipeine                         TS/外部
─────────                       ─────────────                       ────────
                                                                    TeamSpeak 语音
                                                                       │
  [进入功能页]                                                          │
    │  subscribe(feature)                                              │
    ├─────────────────────────────────────►  engine.start_pipeline()   │
    │                                        └─ stt_listen 常驻监听     │
    │                                                      │          │
    │                                                      │◄─────────┤ audio_bus
    │                                                      │          │
    │  ◄── node_update(stt_listen, "识别: 大家好...")       │─ STT ───│
    │                                                      │          │
  [上传图片]                                                      
    │  node_action(input_image, upload)                                  
    ├─────────────────────────────────────►  engine.execute_node()
    │                                        └─ image_input → ocr_01
    │  ◄── node_complete(ocr_01, {text: "..."})
    │
    │                           当 stt_listen 检测到关键词 "暗区"
    │                                        ┌─ ocr_text
    │  ◄── node_complete(stt_listen, trigger)┤
    │                                        └─ stt_text
    │                                        context_build(llm_messages)
    │                                          │
    │  ◄── node_update(llm, "content_chunk")◄──┴─ llm.chat_stream()
    │  ◄── node_complete(llm, {response})
    │                                          │
    │                                          tts.synthesize(response)
    │                                          │
    │                                          ts_output → SEND_VOICE
    │                                                       │
    │  ◄── pipeline_complete                                │
    │                                                       ▼
  [点击重新开始]                                           TeamSpeak 播放
    │  node_action(restart)
    ├─────────────────────────────────────►  engine.delete_instance()
    │                                        engine.start_pipeline()
```

---

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 节点注册 | `@register_node("type")` 装饰器 | 声明式，新增节点只需新建文件+装饰器 |
| 常驻监听 | `listener: True` 标记 | 与 action 节点区分，引擎自动启动 |
| 触发机制 | `trigger.source_node` 配置 | 声明式定义触发链，不在代码里写死 |
| 上下文传递 | `accumulated_context` 字典 + `input_mappings` | 灵活支持多数据源合并 |
| 音频总线 | AudioBus 发布/订阅 | 解耦 ws_teamspeak 和 stt_listen |
| 前端渲染 | 节点类型+状态 → 组件映射表 | 前后端约定一致，新增节点类型只需加映射 |
