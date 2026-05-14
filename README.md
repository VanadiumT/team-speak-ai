# TeamSpeak AI

为 TeamSpeak 语音频道注入 AI 处理能力的三层语音桥接系统——语音识别 → 大模型推理 → 语音合成，让玩家在游戏中通过语音与 AI 实时对话。

## 架构

```
TeamSpeak Client → Java Bridge (:8080) → Python Backend (:8000) → Vue Frontend (:5173)
       ↑                  WebSocket                WebSocket              HTTP dev server
```

| 层 | 技术栈 | 职责 |
|---|--------|------|
| **Bridge** | Java 17, Tomcat Embedded WebSocket, ts3j | 连接 TeamSpeak 服务器，捕获/播放音频 |
| **Backend** | Python 3.11+, FastAPI, Uvicorn | 管线引擎、AI 推理调度、状态管理 |
| **Frontend** | Vue 3, Vite 5, Pinia | 可视化流程编辑器、实时状态渲染 |

### 音频处理流程

```
TeamSpeak 语音 → Java Bridge (ts3j 音频捕获)
  → WS :8080/teamspeak/voice
    → Python AudioBus (发布/订阅)
      → STT 识别 → LLM 推理 → TTS 合成
        → WS :8080/teamspeak/voice
          → Java Bridge → TeamSpeak 播放
```

## 快速开始

### 环境要求

- **Java 17**（bundled in `environment/jdk-17.0.9+9`）
- **Python 3.11+**
- **Node.js 18+**

### 一键启动（Windows）

```bat
.\start-all.bat     # 构建 Java，启动全部 3 个服务（Windows Terminal 多标签页）
.\stop-all.bat      # 按端口停止全部服务
```

### 手动启动

**1. Java Bridge**

```bash
cd team-speak-bot
mvn clean package -DskipTests -q
java -jar target/teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar
```

**2. Python Backend**

```bash
cd team-speak-ai/backend
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入 API Key
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**3. Vue Frontend**

```bash
cd team-speak-ai/frontend
npm install
npm run dev            # Vite dev server on :5173
```

启动后访问 http://localhost:5173 打开可视化编辑器。

## 配置

后端配置通过 `.env` 文件管理，参见 `team-speak-ai/backend/.env.example`。

| 能力 | 可用 Provider | 默认 |
|------|--------------|------|
| STT | `sensevoice`, `whisper`, `minimax` | sensevoice |
| TTS | `edge`, `minimax` | edge |
| LLM | `openai` (MiniMax 兼容) | openai |
| OCR | `easyocr`, `paddleocr` | easyocr |

## 功能特性

- **可视化流程编辑器** — 拖拽节点、连线、画布缩放平移、编辑模式切换
- **管线引擎** — DAG 调度、节点状态实时推送、流式数据输出
- **预设系统** — LLM/TTS/STT/OCR/VAD/TeamSpeak 六类预设，平台+模型两级配置，快速切换
- **变量系统** — 流程局部变量 + 全局持久化跨流程变量
- **撤销/重做** — 每流程 100 步历史，JSONL 持久化
- **通知中心** — 执行通知持久化、分页查询、已读追踪
- **文件上传** — 256KB 分片、断点续传、MIME 校验
- **Material Design 3** — 暗色毛玻璃主题，轻量级 UI
- **WebSocket 统一协议** — 所有通信走信封格式的 `/ws` 端点

## AI 节点

| 节点 | 功能 |
|------|------|
| `start` | 流程入口，自动执行 |
| `ts_input` | TeamSpeak 音频输入源 |
| `stt_listen` | STT + 关键词检测（常驻后台监听） |
| `stt_history` | STT 历史窗口 + 关键词触发 |
| `vad` | WebRTC 语音活动检测 |
| `context_build` | LLM 上下文构建器 |
| `llm` | 大模型推理（思考/输出分离、流式、视觉） |
| `tts` | 文本转语音 |
| `ts_output` | TeamSpeak 音频输出 |
| `audio_player` | 音频播放（流式/批量） |
| `text_input` | 文本输入（静态变量解析 / 交互式等待用户输入） |
| `display_text` | 文本展示/透传 |
| `input_image` | 图片输入 |
| `ocr` | OCR 文字提取 |
| `flow_var_read/write` | 流程变量读写 |
| `sys_var_read/write` | 全局系统变量读写 |

## 项目结构

```
team-speak-ai/
├── start-all.bat, stop-all.bat       # 一键启停脚本
├── environment/                       # 内嵌 JDK 17 + Maven 3.9.9
├── team-speak-bot/                    # Java Bridge（音频中转）
├── team-speak-ai/
│   ├── backend/
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # Pydantic 配置
│   │   ├── api/routes/                # WebSocket 路由
│   │   ├── core/
│   │   │   ├── pipeline/              # 管线引擎（定义、注册、执行、事件）
│   │   │   ├── nodes/                 # 节点实现（17 种节点类型）
│   │   │   ├── flow/                  # 流程管理（CRUD、分组、导入导出）
│   │   │   ├── history/               # 撤销/重做历史
│   │   │   ├── config/                # 预设系统（LLM/TTS/STT/OCR/VAD/TS）
│   │   │   ├── audio/                 # AudioBus 发布/订阅 + 缓冲
│   │   │   ├── variables/             # 系统变量管理
│   │   │   ├── upload/                # 分片文件上传
│   │   │   ├── notification/          # 通知持久化
│   │   │   └── stt/tts/llm/ocr/       # AI Provider 工厂
│   │   └── data/                      # 运行时数据（flows, defaults, history, vars）
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/pipeline/   # 编辑器组件（画布、节点、连线、面板）
│   │   │   ├── stores/                # Pinia 状态管理
│   │   │   └── api/                   # WebSocket 客户端
│   │   └── package.json
│   └── docs/                          # 设计文档（8 篇）
```

## 文档

| 文档 | 内容 |
|------|------|
| [01-系统总览](team-speak-ai/docs/01-系统总览.md) | 项目全貌、服务拓扑、数据流向 |
| [02-架构设计](team-speak-ai/docs/02-架构设计.md) | 架构哲学、通信设计、生命周期 |
| [03-管线系统](team-speak-ai/docs/03-管线系统.md) | 管线抽象模型、端口体系、触发机制 |
| [04-编辑器设计](team-speak-ai/docs/04-编辑器设计.md) | 交互模式、面板系统、撤销重做 |
| [05-预设系统](team-speak-ai/docs/05-预设系统.md) | 通用配置管理、多方案切换 |
| [06-音频管线](team-speak-ai/docs/06-音频管线.md) | AudioBus、回环监听、流式处理 |
| [07-设计系统规范](team-speak-ai/docs/07-设计系统规范.md) | 颜色、字体、组件约定 |
| [08-WebSocket协议规范](team-speak-ai/docs/08-WebSocket协议规范.md) | 信封格式、全部 action 定义 |

## License

Internal project.
