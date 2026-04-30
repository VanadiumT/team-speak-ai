# TeamSpeak AI — 系统架构与数据流设计文档

> 版本: 0.1.0 | 更新: 2026-04-24

---

## 目录

1. [系统总体架构](#1-系统总体架构)
2. [模块层级详述](#2-模块层级详述)
3. [数据流管道](#3-数据流管道)
4. [WebSocket 消息协议](#4-websocket-消息协议)
5. [消息路由与事件总线](#5-消息路由与事件总线)
6. [STT 引擎架构](#6-stt-引擎架构)
7. [LLM 引擎架构](#7-llm-引擎架构)
8. [TTS 引擎架构](#8-tts-引擎架构)
9. [音频缓冲与语音检测](#9-音频缓冲与语音检测)
10. [启动与生命周期](#10-启动与生命周期)
11. [HTTP API 总览](#11-http-api-总览)

---

## 1. 系统总体架构

系统采用 **三层架构**，数据平面和控制平面分离：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3 SPA)                           │
│              port:5173 (Vite Dev)                                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐                 │
│  │WebSocket │  │ Pinia Stores │  │  Components   │                 │
│  │  Client  │  │ app/conversa │  │  AppLayout    │                 │
│  │(自动重连) │  │ tion/files   │  │  FileUploader │                 │
│  └────┬─────┘  └──────────────┘  └───────────────┘                 │
│       │                                                             │
│       │ ws://localhost:8000/ws/client                               │
└───────┼─────────────────────────────────────────────────────────────┘
        │
┌───────┼─────────────────────────────────────────────────────────────┐
│       │          后端层 (Python FastAPI)                             │
│       │              port:8000                                       │
│       ▼                                                             │
│  ┌──────────┐  ┌─────────────────┐  ┌──────────────────┐           │
│  │ws_client │  │  ws_teamspeak   │  │  HTTP Routes     │           │
│  │ 前端连接   │  │ TeamSpeak桥接    │  │ /api/control     │           │
│  │ 会话管理   │  │ 音频缓冲+STT    │  │ /api/tts         │           │
│  │ 事件订阅   │  │ 语音流中继      │  │ /api/files       │           │
│  └──────────┘  └────────┬────────┘  └──────────────────┘           │
│                          │                                          │
│                   ┌──────▼───────┐                                  │
│                   │  Event Bus   │  (发布/订阅)                      │
│                   └──────┬───────┘                                  │
│                          │                                          │
│  ┌──────────┐  ┌─────────▼────────┐  ┌──────────┐                  │
│  │STT Engine│  │  Audio Buffer    │  │TTS Engine│                  │
│  │SenseVoice│  │   per-speaker    │  │ EdgeTTS  │                  │
│  │Whisper   │  │   timeout=2s     │  │MiniMaxTTS│                  │
│  │MiniMax   │  └──────────────────┘  └──────────┘                  │
│  └──────────┘                                                       │
└─────────────────────────────────────────────────────────────────────┘
        │
        │ ws://localhost:8080/teamspeak/voice
        │
┌───────┼─────────────────────────────────────────────────────────────┐
│       │          Java 桥接层 (Spring Boot + Tomcat Embedded)        │
│       │                  port:8080                                   │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              VoiceWebSocketEndpoint                          │    │
│  │        @ServerEndpoint("/teamspeak/voice")                   │    │
│  └────────────────────┬────────────────────────────────────────┘    │
│                       │                                             │
│  ┌────────────────────▼────────────────────────────────────────┐    │
│  │               TeamSpeakVoiceBridge                            │    │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │    │
│  │  │  sendQueue   │  │ dispatchQueue │  │  heartbeatLoop   │  │    │
│  │  │ LinkedBlock  │  │ every 10ms    │  │  every 30s       │  │    │
│  │  │ ingQueue(500)│  │               │  │                  │  │    │
│  │  └──────────────┘  └───────────────┘  └──────────────────┘  │    │
│  └────────────────────┬────────────────────────────────────────┘    │
│                       │                                             │
│  ┌────────────────────▼────────────────────────────────────────┐    │
│  │  TeamSpeak Server (101.34.75.141:1234)                      │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │  ts3j LocalTeamspeakClientSocket                     │   │    │
│  │  │  ├─ setMicrophone(WebSocketAudioSource)              │   │    │
│  │  │  ├─ setVoiceHandler(onReceivedVoice)                 │   │    │
│  │  │  ├─ setWhisperHandler(onReceivedWhisper)             │   │    │
│  │  │  └─ addListener(this)  (TS3Listener 28 event)       │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  WebSocketAudioSource (implements Microphone)                │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │  BlockingQueue<byte[]> audioQueue (capacity=100)     │   │    │
│  │  │  provide() ← ts3j calls every 20ms                  │   │    │
│  │  │  offerAudio() ← called from handleSendVoice()        │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 三层职责

| 层级 | 技术栈 | 核心职责 |
|------|--------|---------|
| **前端层** | Vue 3 + Pinia + Vite | UI 渲染、WebSocket 客户端、状态管理、文件上传 |
| **后端层** | Python FastAPI + uvicorn | 音频处理编排、STT/TTS/LLM 引擎、事件总线、文件存储 |
| **桥接层** | Java 17 + Spring Boot + Tomcat Embedded + ts3j | TeamSpeak 协议接入、语音数据编解码、WebSocket 服务端 |

---

## 2. 模块层级详述

### 2.1 前端层 (team-speak-ai/frontend)

```
src/
├── api/
│   ├── websocket.js        WebSocketClient 类（自定义事件系统，3 秒自动重连）
│   └── files.js            Axios 文件上传 API
├── stores/
│   ├── app.js              全局状态：连接状态、TeamSpeak 状态、STT 事件
│   ├── conversation.js     会话消息：voice_received + stt_result，最多 50 条
│   └── files.js            文件批次管理
├── components/
│   ├── common/
│   │   ├── FileUploader.vue     拖拽/点击上传，支持批次
│   │   └── StatusIndicator.vue  红/绿指示灯组件
│   └── layout/
│       └── AppLayout.vue        主布局：顶栏/侧栏/内容区/底栏日志
├── App.vue                根组件，挂载时初始化 WebSocket
└── main.js                创建 Vue 应用 + Pinia
```

**关键设计：**

- 自定义 `WebSocketClient` 类封装了事件驱动的通信模式，支持 `on()` / `off()` / `emit()`，与后端 EventBus 对应
- 三个 Pinia Store 职责分离：`app` 管连接状态、`conversation` 管语音→STT 消息流、`files` 管文件上传
- 前端不直接连接 TeamSpeak 桥接层，所有通信通过后端中转
- Vite proxy 将 `/api/*` 和 `/ws/*` 转发到后端 8000 端口

### 2.2 后端层 (team-speak-ai/backend)

```
backend/
├── config.py                   Pydantic Settings，统一配置管理
├── main.py                     FastAPI 入口，CORS、路由注册、生命周期
├── api/
│   ├── dependencies.py         依赖注入（占位）
│   └── routes/
│       ├── ws_client.py        前端 WebSocket 端点 /ws/client
│       ├── ws_teamspeak.py     TeamSpeak 桥接端点 /ws/teamspeak（核心）
│       ├── control.py          POST /api/control + GET /api/status
│       ├── files.py            文件上传 CRUD（单文件/批次/删除）
│       └── tts.py              语音合成端点 POST /api/tts/synthesize + GET /api/tts/providers
├── core/
│   ├── audio/
│   │   ├── audio_buffer.py     AudioBuffer 类（按 sender_id 缓冲，2 秒超时）
│   │   └── opus_codec.py       Opus 编解码（占位）
│   ├── llm/
│   │   ├── base.py             BaseLLM 抽象基类 + LLMChunk 数据类
│   │   ├── factory.py          LLMProvider 枚举 + create_llm() 工厂
│   │   └── openai_llm.py       OpenAILLM（OpenAI 兼容 API，支持 MiniMax reasoning）
│   ├── stt/
│   │   ├── base.py             BaseSTT 抽象基类
│   │   ├── factory.py          STTProvider 枚举 + create_stt() 工厂
│   │   ├── sensevoice_stt.py   SenseVoiceSTT（阿里 FunASR，默认引擎）
│   │   ├── whisper_stt.py      WhisperSTT（faster-whisper 本地引擎）
│   │   └── minimax_stt.py      MiniMaxSTT（HTTP API 云端引擎）
│   └── tts/
│       ├── base.py             BaseTTS 抽象基类
│       ├── factory.py          TTSProvider 枚举 + create_tts() 工厂
│       ├── edge_tts.py         EdgeTTS（微软 Edge TTS 免费引擎）
│       └── minimax_tts.py      MiniMaxTTS（WSS 流式引擎）
├── models/
│   ├── upload.py               上传相关 Pydantic 模型
│   └── voice_message.py        VoiceMessage Pydantic 模型
└── services/
    ├── event_bus.py            EventBus 发布/订阅（全局单例）
    ├── file_storage.py         FileStorage JSON 元数据 + 文件系统存储
    └── session_manager.py      SessionManager 会话管理（全局单例）
```

### 2.3 桥接层 (team-speak-bot)

```
team-speak-bot/
├── pom.xml                     Maven: Java 17, ts3j, Tomcat 10 WS, Jackson
└── src/main/
    ├── resources/
    │   └── application.properties    TS/WS 连接配置
    └── java/com/example/teamspeak/
        ├── Main.java                 入口，加载配置，启动桥接
        ├── config/
        │   └── BridgeConfig.java     配置 JavaBean（TS 连接、WS 参数、音频队列容量）
        └── bridge/
            ├── TeamSpeakVoiceBridge.java     核心桥接（TS3Listener + WS 管理）
            ├── VoiceWebSocketEndpoint.java    WebSocket @ServerEndpoint
            ├── WebSocketAudioSource.java      自定义 Microphone 实现
            ├── VoiceMessage.java              消息 POJO（Jackson 序列化）
            └── VoiceMessageType.java          消息类型枚举
```

---

## 3. 数据流管道

### 3.1 上行语音管道 (TeamSpeak → STT → 前端显示)

这是系统最核心的数据路径，从 TeamSpeak 用户语音到前端看到转写文本：

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                        上行语音管道                                        │
 │                                                                         │
 │ TeamSpeak Server                                                        │
 │    │  (ts3j 协议，OPUS_VOICE 编码音频帧)                                    │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ TeamSpeakVoiceBridge.onReceivedVoice(voice)                     │    │
 │ │    │  从 PacketBody0Voice 提取 codecData (原始 Opus 帧)           │    │
 │ │    │  构造 VoiceMessage(type=VOICE, senderId, senderName,       │    │
 │ │    │    codecType, timestamp, sequence, data=Base64(codecData)) │    │
 │ │    │  送入 sendQueue (LinkedBlockingQueue, 容量 500)            │    │
 │ │    ▼                                                             │    │
 │ │ dispatchVoiceQueue()  (ScheduledExecutor, 每 10ms 执行)          │    │
 │ │    │  从 sendQueue poll 出 VoiceMessage                          │    │
 │ │    │  Jackson → JSON 字符串                                      │    │
 │ │    │  session.getBasicRemote().sendText(json)                   │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 │    │  WebSocket JSON 消息                                               │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ ws_teamspeak.py  TeamSpeakWebSocket.receive_message()            │    │
 │ │    │  async for 循环接收消息                                       │    │
 │ │    │  json.loads() 解析 JSON                                      │    │
 │ │    │  parse_message() 标准化为内部 dict                            │    │
 │ │    ▼                                                             │    │
 │ │ 消息转发：websocket.send_json(parsed) (中继到前端)                  │    │
 │ │    │                                                             │    │
 │ │ 音频缓冲：                                                         │    │
 │ │    │  audio_buffer.add_frame(sender_id, frame, seq, ts)          │    │
 │ │    │  按 sender_id 独立缓冲音频帧                                  │    │
 │ │    │                                                             │    │
 │ │ 语音结束检测：                                                      │    │
 │ │    │  if len(frame_data) < 1000 AND audio_buffer.is_complete():  │    │
 │ │    │    → 进入 STT 管道                                          │    │
 │ │    ▼                                                             │    │
 │ │ process_complete_audio(sender_id, sender_name, timestamp)        │    │
 │ │    │  1. audio_buffer.get_audio(sender_id) 合并所有帧              │    │
 │ │    │  2. stt.transcribe(audio_data) 异步转写                      │    │
 │ │    │     (SenseVoice: ThreadPoolExecutor + FunASR 模型)          │    │
 │ │    │  3. broadcast_teamspeak_event("stt_result", {...})          │    │
 │ │    │     → event_bus.broadcast_to_subscribers("stt_result",...) │    │
 │ │    │  4. audio_buffer.clear(sender_id)                           │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 │    │  EventBus 分发                                                    │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ ws_client.py 前端 WebSocket                                     │    │
 │ │    │  前端订阅了 "stt_result" 事件                                │    │
 │ │    │  EventBus 向所有订阅者发送                                    │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 │    │                                                                     │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ 前端 conversation Store                                          │    │
 │ │    │  wsClient.on('stt_result', data) → 更新 items 列表          │    │
 │ │    │  每条消息 = {speaker, stt text, timestamp}                   │    │
 │ │    │  最多保留 50 条，新消息插入头部                                │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────────────────────────┘
```

**关键时序：**
- TeamSpeak Voice Bridge 每 10ms 检查并发送语音队列
- 后端 AudioBuffer 超时 2 秒判定说话结束
- 帧大小 < 1000 bytes 触发完整检测
- STT 转为文本后立即广播

### 3.2 下行语音管道 (前端/后端 → TeamSpeak 播放)

反向路径：将音频注入到 TeamSpeak 的麦克风流中，让机器人"说话"：

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                        下行语音管道                                        │
 │                                                                         │
 │ 前端 / 后端                                                              │
 │    │  发送 SEND_VOICE 消息                                              │
 │    │  { type: "SEND_VOICE", data: "<Base64 audio>", timestamp }        │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ TeamSpeakWebSocket.send_voice_message(audio_data)                │    │
 │ │    │  构造 JSON 消息发送到 TeamSpeak 桥接                          │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 │    │  WebSocket → ws://localhost:8080/teamspeak/voice                  │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ VoiceWebSocketEndpoint.onOpen → addMessageHandler(String.class)  │    │
 │ │    │  → TeamSpeakVoiceBridge.onWsMessage(text, session)          │    │
 │ │    ▼                                                             │    │
 │ │ handleMessage(VoiceMessage)                                       │    │
 │ │    │  type == SEND_VOICE                                         │    │
 │ │    │  → handleSendVoice(msg)                                     │    │
 │ │    │    1. Base64.getDecoder().decode(msg.getData())              │    │
 │ │    │    2. audioSource.offerAudio(audioData)                      │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 │    │  BlockingQueue<byte[]>                                            │
 │    ▼                                                                     │
 │ ┌──────────────────────────────────────────────────────────────────┐    │
 │ │ WebSocketAudioSource.provide()  (被 ts3j 每 20ms 调用)             │    │
 │ │    │  audioQueue.poll(25ms timeout)                               │    │
 │ │    │  ts3j → TeamSpeak Server → 频道内所有用户听到                 │    │
 │ └──────────────────────────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 控制命令管道

```
前端 ───→ ws_client.py ──→ ws_teamspeak.py ──→ TeamSpeakVoiceBridge
  │                          │                       │
  │ teamspeak_connect        ts_client.connect()     handleControl("connect")
  │ teamspeak_disconnect     ts_client.disconnect()  handleControl("disconnect")
  │ teamspeak_control        ts_client.send_control  handleControl("mute"|"unmute")
  │                           (action, params)
```

### 3.4 文件上传管道

```
前端 (FileUploader.vue)
  │  POST /api/files/upload  (multipart/form-data)
  │  function_id, batch_id, metadata
  ▼
FileStorage (services/file_storage.py)
  │  ./uploads/{function_id}/{batch_id}/{file_id}
  │  metadata.json 索引所有文件元数据
  │  支持单文件/批次上传/删除全部
```

### 3.5 完整 AI Pipeline（LLM/TTS 回传部分未接入管道）

当前实现状态：
- **STT**: 已完整接入音频管道，`VOICE` 消息 → 缓冲 → STT → 广播 `stt_result`
- **LLM**: 代码已实现 (`OpenAILLM`)，配置已就绪 (`MiniMax-M2.7`)，但 **未接入语音管道**
- **TTS**: 代码已实现，作为独立 HTTP 端点 (`/api/tts/synthesize`)，但 **未接入语音管道**

完整预期管道（STT→LLM→TTS→回传）：

```
TeamSpeak Audio
  → Voice Bridge (Java)                          ✅
    → AudioBuffer                                 ✅
      → STT (SenseVoice)                          ✅
        → broadcast stt_result to frontend        ✅
        → [LLM 推理 → LLMChunk(content+reason)]  ⏳ 代码就绪，未管道化
          → broadcast llm_result to frontend      ❌ 未实现
          → TTS synthesize(content)               ⏳ 代码就绪，未管道化
            → SEND_VOICE → Voice Bridge           ❌ 未实现
              → TeamSpeak 频道播放                 ❌ 未实现
```

---

## 4. WebSocket 消息协议

### 4.1 桥接层 ↔ 后端层 (Java ↔ Python) 协议

**端点**: `ws://localhost:8080/teamspeak/voice`

| 方向 | 类型 | 字段 | 说明 |
|------|------|------|------|
| Bridge→Backend | `VOICE` | senderId, senderName, codecType, timestamp, sequence, data | 频道语音，data=Base64(Opus帧) |
| Bridge→Backend | `WHISPER` | senderId, senderName, targetId, codecType, timestamp, sequence, data | 私聊语音 |
| Bridge→Backend | `HEARTBEAT` | type, timestamp | 心跳响应 |
| Bridge→Backend | `CONTROL` | type, action, data | 控制通知（"connected"等） |
| Bridge→Backend | `ERROR` | code, message | 错误通知 |
| Backend→Bridge | `SEND_VOICE` | type, data, timestamp | 注入音频到 TeamSpeak |
| Backend→Bridge | `SILENCE` | type, timestamp | 静音信号 |
| Backend→Bridge | `CONTROL` | type, action, timestamp, params | 控制命令（mute/unmute/disconnect） |
| Backend→Bridge | `HEARTBEAT` | type, timestamp | 心跳请求 |

### 4.2 后端层 ↔ 前端层 (Python ↔ JavaScript) 协议

**端点**: `ws://localhost:8000/ws/client`

| 方向 | 类型 | 说明 |
|------|------|------|
| BE→FE | `teamspeak_connected` | TeamSpeak 连接状态变更 |
| BE→FE | `status` | 服务状态（含 teamspeak_connected） |
| BE→FE | `stt_result` | STT 转写结果 | 
| BE→FE | `subscribed` / `unsubscribed` | 事件订阅确认 |
| BE→FE | `teamspeak_status` | TeamSpeak 操作结果 |
| BE→FE | `control_sent` | 控制命令已发送确认 |
| FE→BE | `ping` | WebSocket 心跳（响应 `pong`） |
| FE→BE | `subscribe` / `unsubscribe` | 事件订阅管理 |
| FE→BE | `teamspeak_connect` / `teamspeak_disconnect` | 连接控制 |
| FE→BE | `teamspeak_control` | 发送控制命令 |
| FE→BE | `get_status` | 查询状态 |

### 4.3 后端层内部路由 (ws/teamspeak 端点)

**端点**: `ws://localhost:8000/ws/teamspeak`

这是一个**内部 WebSocket 端点**，用于前端直接与 TeamSpeak 桥接层通信的通道。消息类型与桥接层协议兼容。

### 4.4 消息格式规范

所有层级的消息使用统一的 JSON 信封格式：

```json
{
  "type": "EVENT_TYPE",
  "data": { /* 具体事件数据 */ },
  "timestamp": 1713912345678
}
```

---

## 5. 消息路由与事件总线

### 5.1 EventBus 架构

`EventBus` 是后端层的消息中枢，实现发布-订阅模式：

```python
# services/event_bus.py 核心数据结构
EventBus:
    _websockets: Dict[str, WebSocket]    # client_id → WebSocket
    _subscribers: Dict[str, Set[str]]    # event_type → {client_id, ...}
```

**核心方法：**

| 方法 | 功能 |
|------|------|
| `register_websocket(client_id, ws)` | 注册客户端连接 |
| `unregister_websocket(client_id)` | 注销客户端 + 清理所有订阅 |
| `broadcast(event_type, data)` | 广播到所有已连接客户端 |
| `broadcast_to_client(client_id, event_type, data)` | 发送到指定客户端 |
| `broadcast_to_subscribers(event_type, data, exclude_client)` | 发送到某事件的订阅者 |
| `subscribe(event_type, client_id)` | 客户端订阅事件 |
| `unsubscribe(event_type, client_id)` | 客户端取消订阅 |

### 5.2 消息路由图

```
                    ┌─────────────────────┐
                    │  TeamSpeak Voice    │
                    │  Bridge (Java:8080) │
                    └─────────┬───────────┘
                              │ JSON (VOICE/WHISPER/HEARTBEAT)
                              ▼
                    ┌─────────────────────┐
                    │  ws_teamspeak.py    │
                    │  /ws/teamspeak      │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ audio_buffer  │  │
                    │  │ (per-speaker) │  │
                    │  └──────┬────────┘  │
                    │         │ STT       │
                    │         ▼           │
                    │  ┌───────────────┐  │
                    │  │    STT        │  │
                    │  │   Engine      │  │
                    │  └──────┬────────┘  │
                    │         │ result    │
                    │         ▼           │
                    │  broadcast_event()  │
                    └─────────┬───────────┘
                              │ stt_result
                              ▼
                    ┌─────────────────────┐
                    │     EventBus        │
                    │  broadcast_to_      │
                    │  subscribers()       │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  ws_client.py       │
                    │  /ws/client         │
                    │  ClientSession      │
                    │  client_sessions[]  │
                    └─────────┬───────────┘
                              │ JSON
                              ▼
                    ┌─────────────────────┐
                    │  Vue Frontend       │
                    │  WebSocketClient    │
                    │  → app store        │
                    │  → conversation     │
                    │    store            │
                    └─────────────────────┘
```

### 5.3 订阅机制

前端通过 WebSocket 发送 `subscribe` / `unsubscribe` 消息管理事件监听：

```javascript
// 前端订阅
wsClient.send('subscribe', { events: ['stt_result', 'voice_received'] });

// 前端取消订阅
wsClient.send('unsubscribe', { events: ['stt_result'] });
```

---

## 6. STT 引擎架构

### 6.1 工厂模式

```python
STTProvider 枚举:
    WHISPER    → WhisperSTT (faster-whisper, 本地 GPU)
    MINIMAX    → MiniMaxSTT (HTTP API, 云端)
    SENSEVOICE → SenseVoiceSTT (FunASR, 本地 CPU/GPU, 默认)
```

### 6.2 SenseVoiceSTT 实现细节

```
transcribe(audio_data: bytes) → str
  │
  ├─ _resample_audio() : 原始 Opus (48kHz) → 16kHz PCM
  │    ├─ soundfile.load() 加载 bytes
  │    ├─ scipy.signal.resample() 到 16000 Hz
  │    └─ 归一化 int16 bytes
  │
  ├─ _write_wav(tempfile) : PCM → WAV 容器
  │
  ├─ model.generate() : FunASR SenseVoiceSmall
  │    ├─ language="auto" (自动检测中/英/日/韩)
  │    ├─ use_itn=True (逆文本正则化，数字/标点规范化)
  │    └─ batch_size_s=60
  │
  ├─ rich_transcription_postprocess(text) : 富文本后处理
  │
  └─ ThreadPoolExecutor(max_workers=2) : 异步非阻塞包装
```

### 6.3 STT 选择依据

| 引擎 | 延迟 | 准确性 | 离线 | 成本 |
|------|------|--------|------|------|
| SenseVoice | 低 (本地推理) | 高 (中文优化) | ✅ | 免费 |
| Whisper | 中 (本地GPU) | 高 (多语言) | ✅ | 免费 |
| MiniMax | 高 (网络API) | 非常高 | ❌ | 按量计费 |

---

## 7. LLM 引擎架构

### 7.1 工厂模式

```python
LLMProvider 枚举:
    OPENAI → OpenAILLM (OpenAI 兼容 API，默认 MiniMax-M2.7)
```

### 7.2 OpenAILLM (MiniMax 兼容)

后端目前配置为通过 **MiniMax OpenAI 兼容 API** 调用 `MiniMax-M2.7` 模型，使用 `openai` Python 库：

```
config.py:
    openai_api_key: str = ""
    openai_base_url: str = "https://api.minimaxi.com/v1"
    openai_model: str = "MiniMax-M2.7"
    openai_reasoning_split: bool = True
```

#### OpenAILLM.chat(messages) → LLMChunk

```
  │
  ├─ AsyncOpenAI(api_key, base_url) 创建客户端
  ├─ extra_body["reasoning_split"] = True  (MiniMax 特有)
  ├─ client.chat.completions.create(stream=True)
  │
  ├─ 流式处理每个 chunk:
  │   ├─ delta.reasoning_details → reasoning_full
  │   └─ delta.content → content_full
  │
  └─ 返回 LLMChunk(content, reasoning)
```

#### OpenAILLM.chat_stream(messages) → AsyncIterator[LLMChunk]

```
  │  流式逐块返回:
  │  yield LLMChunk(
  │      content=delta.content,       # 新增文本片段
  │      reasoning=reasoning_buffer   # 累积的思考过程
  │  )
```

### 7.3 LLMChunk 数据结构

```python
@dataclass
class LLMChunk:
    content: str = ""      # 实际回复文本
    reasoning: str = ""    # 思考过程（前端可单独显示 reasoning 气泡）
```

### 7.4 集成状态

> **当前状态**: LLM 模块代码已实现（base.py / factory.py / openai_llm.py），配置已设置，但 **尚未接入语音管道**。当前 `process_complete_audio()` 在 STT 转写完成后只广播 `stt_result`，未调用 LLM。

预期完整链接路径：

```
process_complete_audio()
  │
  ├─ 1. stt.transcribe(audio_data) → text  ✅ 已实现
  │
  ├─ 2. llm.chat(=[{role: "user", text}]) → LLMChunk  ⏳ 未实现
  │     └─ 需要: 会话上下文管理 + system prompt
  │
  └─ 3. tts.synthesize(content) → audio_bytes  ⏳ 未实现
        └─ 需要: 通过 SEND_VOICE 注入 TeamSpeak
```

---

## 8. TTS 引擎架构

### 7.1 工厂模式

```python
TTSProvider 枚举:
    EDGE    → EdgeTTS (微软 Edge TTS, HTTP 流式)
    MINIMAX → MiniMaxTTS (MiniMax T2A v2, WSS 流式)
```

### 7.2 EdgeTTS

```
synthesize(text: str) → bytes
  │  edge-tts 库 → Microsoft Edge TTS 服务
  │ 默认语音: zh-CN-XiaoxiaoNeural
  │ 流式收集所有 chunk → 合并为完整音频 bytes
  │
synthesize_stream(text: str) → AsyncGenerator[bytes]
  │ yield 每个音频 chunk
```

### 7.3 MiniMaxTTS

```
synthesize_stream(text: str) → AsyncGenerator[bytes]
  │
  ├─ _connect() : WSS → wss://api.minimaxi.com/ws/v1/t2a_v2
  │    ├─ Authorization: Bearer {api_key}
  │    └─ 等待 connected_success 事件
  │
  ├─ _start_task(ws) : 发送 voice_setting + audio_setting
  │    ├─ voice: male-qn-qingse (默认男声)
  │    ├─ sample_rate: 32000, bitrate: 128k, format: mp3
  │    └─ 等待 task_started 事件
  │
  ├─ task_continue : 发送文本
  │
  ├─ 接收音频 chunk (hex → bytes)
  │    └─ yield 每个 chunk
  │
  └─ task_finish : 清理连接
```

---

## 8. 音频缓冲与语音检测

### 8.1 AudioBuffer 设计

```python
class AudioBuffer:
    """
    核心数据结构:
    _buffers: Dict[int, dict]    # sender_id → 缓冲状态
        {
            "frames": [bytes, ...],     # 音频帧列表
            "start_time": datetime,      # 第一帧到达时间
            "last_sequence": int,        # 最后一帧序号
            "last_timestamp": int,       # 最后一帧时间戳
        }
    timeout: float = 2.0                # 说话结束判定超时
    """
```

### 8.2 语音端点检测逻辑

```
接收 VOICE/WHISPER 消息:
  │
  ├─ base64.b64decode(data) → frame_data (bytes)
  │
  ├─ audio_buffer.add_frame(sender_id, frame_data, seq, ts)
  │    首次 → 创建新缓冲并记录 start_time
  │    已有 → 追加帧
  │
  └─ if len(frame_data) < 1000                 # 帧大小阈值
       AND audio_buffer.is_complete(sender_id): # 超时 2 秒
     →
         process_complete_audio(sender_id, name, ts)
```

**使用两个条件判定说话结束：**
1. **帧大小阈值**: 当前帧 < 1000 bytes（可能表示静音/说话结束）
2. **超时检测**: 距第一帧到达超过 2 秒

两个条件同时满足才进入 STT 流程，避免过早触发。

### 8.3 Java 侧音频队列

```java
// TeamSpeakVoiceBridge
BlockingQueue<VoiceMessage> sendQueue = new LinkedBlockingQueue<>(500);
// onReceivedVoice/onReceivedWhisper → sendQueue.offer(msg)
// dispatchVoiceQueue() 每 10ms 执行 → sendQueue.poll() → WebSocket send

// WebSocketAudioSource
BlockingQueue<byte[]> audioQueue = new LinkedBlockingQueue<>(100);
// offerAudio() → audioQueue.offer()
// provide() → audioQueue.poll(25ms) 被 ts3j 每 20ms 调用
```

---

## 9. 启动与生命周期

### 9.1 整体启动顺序

```
start-all.bat
  │
  ├─ [1/3] Java 桥接层
  │    mvn clean package -DskipTests
  │    java -jar teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar
  │    │
  │    ├─ 初始化 ts3j LocalTeamspeakClientSocket
  │    ├─ 生成 LocalIdentity (security level 22)
  │    ├─ 启动嵌入式 Tomcat, WebSocket 端口 8080
  │    ├─ 注册调度任务:
  │    │   ├─ dispatchVoiceQueue() 每 10ms
  │    │   └─ sendHeartbeat() 每 30s
  │    ├─ 连接 TeamSpeak 服务器
  │    └─ 等待 WebSocket 连接
  │
  ├─ [2/3] Python 后端
  │    uvicorn main:app --host 0.0.0.0 --port 8000
  │    │
  │    ├─ FastAPI 启动
  │    ├─ CORS 中间件 (allow all origins)
  │    ├─ 注册 5 个路由器
  │    └─ startup_event():
  │        └─ ts_client.connect() 自动连接 Java 桥接层
  │
  └─ [3/3] Vue 前端
       npm run dev (port 5173)
       │
       └─ Vite proxy: /api → localhost:8000, /ws → ws://localhost:8000
```

### 9.2 重连机制

| 组件 | 策略 | 参数 |
|------|------|------|
| Java→TeamSpeak | 断开后 5 秒自动重连，失败后 10 秒指数退避 | 硬编码 |
| Python→Java Bridge | 最多 10 次尝试，间隔 = ts_reconnect_interval × attempt | 5~50 秒 |
| 前端→Python Backend | 无限重连，固定间隔 3 秒 | ws_reconnect_interval |

### 9.3 心跳机制

```
Java 桥接层: 每 30 秒发送 HEARTBEAT 消息
Python 后端: 每 25 秒发送 HEARTBEAT 消息（ws_teamspeak heartbeat_loop）
前端: 通过 ping/pong 消息保持连接
```

---

## 10. HTTP API 总览

### 10.1 控制 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查+TeamSpeak连接状态 |
| POST | `/api/control` | 控制命令 (connect/disconnect/send_voice) |
| GET | `/api/status` | 服务状态 |

### 10.2 TeamSpeak WebSocket 管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/ws/teamspeak/status` | 获取TeamSpeak连接状态 |
| POST | `/ws/teamspeak/connect` | 主动连接TeamSpeak Voice Bridge |
| POST | `/ws/teamspeak/disconnect` | 断开TeamSpeak连接 |

### 10.3 客户端会话 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/ws/client/sessions` | 列出所有前端连接 |
| GET | `/ws/client/sessions/{client_id}` | 获取特定会话详情 |

### 10.4 TTS API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/tts/synthesize` | 文本转语音合成 |
| GET | `/api/tts/providers` | 获取可用TTS提供商列表 |

### 10.5 文件 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/files/upload` | 上传单文件 |
| POST | `/api/files/upload/batch` | 批量上传 |
| GET | `/api/files/batch/{batch_id}` | 获取批次文件列表 |
| GET | `/api/files/files/{file_id}` | 获取文件信息 |
| GET | `/api/files/files/{file_id}/content` | 获取文件内容 |
| DELETE | `/api/files/batch/{batch_id}` | 删除批次 |
| DELETE | `/api/files/files/{file_id}` | 删除单文件 |
| DELETE | `/api/files/all` | 删除所有上传文件 |

---

## 附录 A: 配置参考

### 后端配置 (config.py / .env)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `host` | `0.0.0.0` | 后端监听地址 |
| `port` | `8000` | 后端监听端口 |
| `ts_ws_url` | `ws://localhost:8080/teamspeak/voice` | Java 桥接 WebSocket 地址 |
| `stt_provider` | `sensevoice` | STT 引擎选择 (whisper/minimax/sensevoice) |
| `tts_provider` | `edge` | TTS 引擎选择 (edge/minimax) |
| `llm_provider` | `openai` | LLM 提供商 (配置为 MiniMax 兼容) |
| `openai_base_url` | `https://api.minimaxi.com/v1` | MiniMax OpenAI 兼容 API |
| `openai_model` | `MiniMax-M2.7` | LLM 模型 |

### Java 桥接配置 (application.properties)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ts.host` | `101.34.75.141` | TeamSpeak 服务器地址 |
| `ts.port` | `1234` | TeamSpeak 服务器端口 |
| `ts.password` | `MySecurePassword123` | TeamSpeak 服务器密码 |
| `ts.nickname` | `ROTBOT` | 机器人昵称 |
| `ws.port` | `8080` | WebSocket 服务端口 |
| `ws.path` | `/teamspeak/voice` | WebSocket 端点路径 |
| `audio.codec` | `OPUS_VOICE` | 音频编码类型 |
| `audio.voiceQueueCapacity` | `500` | 语音发送队列容量 |
| `audio.microphoneQueueCapacity` | `100` | 麦克风注入队列容量 |
| `heartbeat.intervalSeconds` | `30` | 心跳间隔 |

---

## 附录 B: 项目文件索引

```
E:\programmetemp\project\team_speak_ai\
├── start-all.bat / stop-all.bat           # Windows 启停脚本
├── .gitignore
│
├── team-speak-ai/                          # 主应用 (Python + Vue)
│   ├── backend/                            # FastAPI 后端 (25 文件)
│   │   ├── config.py                       # 配置
│   │   ├── main.py                         # 入口
│   │   ├── api/routes/                     # 路由 (6 文件)
│   │   ├── core/                           # 核心 (14 文件)
│   │   ├── models/                         # 数据模型 (2 文件)
│   │   └── services/                       # 服务 (3 文件)
│   │
│   └── frontend/                           # Vue 前端 (11 文件)
│       └── src/                            # (8 文件)
│
└── team-speak-bot/                         # Java 桥接 (8 文件)
    └── src/main/java/com/example/teamspeak/
        ├── Main.java                       # 入口
        ├── config/                         # 配置
        └── bridge/                         # 桥接核心 (5 文件)
```
