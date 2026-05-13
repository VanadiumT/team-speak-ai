# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeamSpeak AI — a three-tier voice bridge that adds AI processing (STT, LLM, TTS, OCR) to TeamSpeak. Three independent services connected via WebSocket.

| Tier | Stack | Port |
|------|-------|------|
| Bridge | Java 17, Maven, Tomcat Embedded WebSocket, ts3j | 8080 |
| Backend | Python 3.11+, FastAPI, Uvicorn | 8000 |
| Frontend | Vue 3, Vite 5, Pinia | 5173 |

## Common Commands

### Start all services (Windows)
```bat
.\start-all.bat        # builds Java, then launches all 3 services in parallel
.\stop-all.bat         # kills all 3 processes by port
```

### Java bridge (`team-speak-bot/`)
```bash
# Uses bundled JDK 17 and Maven 3.9.9 from environment/
mvn clean package -DskipTests -q
java -jar target/teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar
```

### Python backend (`team-speak-ai/backend/`)
```bash
pip install -r requirements.txt      # install deps (also has pyproject.toml for Poetry)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Vue frontend (`team-speak-ai/frontend/`)
```bash
npm install
npm run dev         # Vite dev server on :5173, proxies /ws -> ws://:8000
npm run build       # production build
```

## Architecture

### Service communication (target architecture)
- **Java ↔ Python**: WebSocket `ws://localhost:8080/teamspeak/voice`. Java is the server, Python connects as client via `api/routes/ws_teamspeak.py`. This is an **internal audio bridge** — the frontend does NOT connect to it directly. Supports loopback mode (audio routed back to TeamSpeak client).
- **Python ↔ Frontend**: Single unified WebSocket `ws://localhost:8000/ws` using the **envelope protocol**. All flow management, node editing, file upload, execution control, notifications, presets CRUD, system variables go through this one endpoint.

### Protocol (envelope format)
All messages on `/ws` use a unified envelope: `{msg_id, flow_id, type, action, params, ts}`. Full spec in `team-speak-ai/docs/08-WebSocket协议规范.md`, architecture overview in `team-speak-ai/docs/01-系统总览.md` and `team-speak-ai/docs/02-架构设计.md`.

WebSocket heartbeat: client sends `ping` every 30s, expects `pong` within 90s. Server disconnects clients inactive for >90s.

### Audio flow (TeamSpeak → AI processing)
```
TeamSpeak → Java Bridge (ts3j) → WS :8080 → Python ws_teamspeak.py
  → AudioBus (pub/sub) → stt_listen_node (STT + keyword detection)
  → triggers downstream nodes → TTS → WS :8080 → Java → TeamSpeak playback
```

### Pipeline engine (`core/pipeline/`)
The central orchestration system. Pipelines are defined as JSON files in `data/flows/`.

Frontend workflow editor features:
- Edit mode toggle (default is flow view mode)
- Node palette with drag-to-canvas creation
- Port drag connection with temp line preview
- Canvas pan (middle-mouse) and zoom (scroll wheel)
- Node deletion and connection management
- On-demand port visibility management (NodeIOMgmt panel)

Key files:
- `definition.py` — `NodeTypeDef`, `PortDef`, `PortsDef`, `TabDef`, `NodeDefinition`, `PipelineDefinition`, `ConnectionDef`, `FlowSummary`, `InputMapping`, `TriggerConfig` data classes. Port system has `data_type` (string, string_array, messages, image, audio, event, number, any), `visibility` (always/on-demand), and `repeatable` ports (with group/min/max).
- `registry.py` — `NodeRegistry`: `@register_node()` decorator for node class registration, `list_type_defs()` returns full type metadata (ports, tabs, colors) for frontend
- `engine.py` — `PipelineEngine` singleton: loads flows, manages instances, executes nodes, handles WS subscriptions. Key behaviors:
  - **Streaming chain detection**: auto-detects `producer -> consumer` chains on `stream-*` ports and pipelines them with async queues
  - **Listener lifecycle**: background nodes (marked `listener: true`) run in continuous async loops with cancel/timeout/error handling
  - **`accumulated_context`**: shared dict with preset keys (`ocr_texts`, `stt_history`, `llm_messages`, `skill_prompt`) for cross-node data accumulation
  - **Connection-to-node sync**: `_sync_connections_to_nodes()` converts `connections[]` array into per-node `trigger` and `input_mapping` configs
- `emitter.py` — `EventEmitter`: pushes real-time events (`node.status_changed`, `node.log_entry`, `pipeline.started/completed`) to subscribed WS clients; auto-persists important updates to notification system
- `context.py` — `NodeContext`, `NodeOutput`, `NodeState` (enum: IDLE/STARTING/RUNNING/COMPLETED/ERROR/CANCELLED/PAUSED), `NodeRuntime`, `_STREAM_END` sentinel

### Logging (`core/logger/`)
- `factory.py` — Creates loggers; `LoggingHandler` bridges standard `logging` to pipeline event system
- `file_logger.py` — `FileLogger`: daily-rotated JSONL logs with configurable retention

Nodes live in `core/nodes/`. Each node extends `BaseNode` and implements `execute(context, emit) -> NodeOutput`. Nodes are registered via `@NodeRegistry.register("node_name")` and imported in `core/nodes/__init__.py`.

Available node types (extensible — register new types via `@NodeRegistry.register()`):
- `start` — Flow entry point: auto-executes, writes `init_params` into `accumulated_context`
- `input_image` — Image input node
- `ocr` — OCR text extraction
- `ts_input` — TeamSpeak audio input source (subscribes to AudioBus)
- `stt_listen` — STT with keyword detection (persistent background listener node with loopback support)
- `stt_history` — STT history + keyword trigger (maintains history window, detects keywords)
- `vad` — Voice Activity Detection (WebRTC VAD, segments PCM audio into sentences)
- `context_build` — Context builder for LLM
- `llm` — LLM inference node (supports thinking/output separation, streaming, vision)
- `tts` — Text-to-speech output
- `ts_output` — TeamSpeak audio output (MP3 decoding + PCM streaming)
- `audio_player` — Audio playback with streaming/batch paths
- `text_input` — Text input (static with variable resolution, or interactive — pauses flow for user input)
- `display_text` — Text display/passthrough with `$param.key` and `$sys.key` variable resolution
- `flow_var_read` — Read from flow-local `accumulated_context`
- `flow_var_write` — Write to flow-local `accumulated_context` (overwrite/append modes)
- `sys_var_read` — Read from global persistent `SysVarManager`
- `sys_var_write` — Write to global persistent `SysVarManager`

### Flow management (`core/flow/`)
- `manager.py` — `FlowManager`: CRUD for flow JSON files, sidebar tree generation, node/connection position persistence, DAG cycle detection, port validation, group hierarchy persistence (`groups.json`), ZIP export/import for groups

### History / undo-redo (`core/history/`)
- `manager.py` — `HistoryManager`: per-flow undo/redo stacks (max 100 entries each), JSONL persistence, 500ms merge window for config updates

### Default config (`core/config/`)
- `defaults.py` — `ConfigDefaultsManager`: load/save per-node-type default configs from `data/defaults/`. Also contains all 6 preset managers (see below).

### Presets system (`core/config/defaults.py`)
Two-tier "platform + model" preset architecture for each AI capability. Each preset manager supports CRUD via WebSocket, persisted to `data/defaults/*.json`, with `get_effective_config(platform_id, model_id, overrides)` that merges platform settings, model config, and node-level overrides (falls back to global `settings` when API keys/URLs are empty).

| Preset Manager | Config file | Key model params |
|---|---|---|
| `PresetManager` (LLM) | `llm_presets.json` | provider, base_url, api_key, temperature, max_tokens, streaming, thinking_mode, vision, system_prompt |
| `TtsPresetManager` (TTS) | `tts_presets.json` | provider, api_key, voice_id, speed, vol, pitch, emotion, sample_rate, format, streaming |
| `SttPresetManager` (STT) | `stt_presets.json` | provider, api_key, api_url, model_dir, device, language, sample_rate |
| `OcrPresetManager` (OCR) | `ocr_presets.json` | provider, det_model_dir, rec_model_dir, lang_list, gpu, use_angle_cls |
| `VadPresetManager` (VAD) | `vad_presets.json` | provider (webrtcvad), vad_mode (0-3), frame_duration_ms, hangover_ms, min_speech_ms |
| `TeamSpeakPresetManager` | `ts_presets.json` | ws_url, api_key, nickname, auto_reconnect, reconnect_delay |

### System variables (`core/variables/`)
- `manager.py` — `SysVarManager`: global cross-flow persistent KV store, saved to `data/system_vars.json`. Supports get/set (overwrite/append)/delete. Read/written by `sys_var_read`/`sys_var_write` nodes. Frontend store: `stores/sysvars.js`.

### File upload (`core/upload/`)
- `chunk_receiver.py` — `ChunkReceiver`: binary frame file upload with resume support, 256KB chunks, magic byte validation

### Audio bus (`core/audio/`)
- `audio_bus.py` — publish/subscribe bus: `ws_teamspeak.py` publishes incoming audio, `stt_listen_node` consumes it
- `audio_buffer.py` — per-speaker audio buffering with timeout and voice activity detection

### Notification (`core/notification/`)
- `manager.py` — `NotificationManager`: JSONL per-flow persistence, cursor-based pagination, read state tracking, 7-day auto-cleanup. Integrated via `emitter.py` (auto-persist on `emit_important_update`) and `ws_main.py` (`notification.list`, `notification.mark_read` commands)

### Provider factories
Each AI capability has a factory pattern with swappable backends. Runtime config is resolved via the presets system (platform + model tiers), with global `config.py` / `.env` as fallback.

| Capability | Config key | Available providers | Code path |
|-----------|------------|-------------------|-----------|
| STT | `stt_provider` | `sensevoice` (default), `whisper`, `minimax` | `core/stt/factory.py` |
| TTS | `tts_provider` | `edge` (default), `minimax` | `core/tts/factory.py` |
| LLM | `llm_provider` | `openai` (default, OpenAI-compatible — points to MiniMax API) | `core/llm/factory.py` |
| OCR | `ocr_provider` | `easyocr` (default), `paddleocr` | `core/ocr/factory.py` |
| VAD | — | `webrtcvad` (built-in) | `core/nodes/vad_node.py` |

### Data persistence
```
backend/data/
  flows/           # Flow JSON files (one per flow)
  groups.json      # Directory/group hierarchy persistence
  system_vars.json # Global cross-flow persistent variables (SysVarManager)
  defaults/        # Per-node-type default configs + presets (llm/tts/stt/ocr/vad/ts_presets.json)
  history/         # Per-flow operation history JSONL (for undo/redo)
  uploads/         # Uploaded files (by upload_id)
  notifications/   # Per-flow notification history JSONL + read_state.json
```

### Frontend state management
- `stores/editor.js` — Pinia store for flow editing state: nodes, connections, undo/redo, drag-and-drop, debounced config updates, edit mode toggle, dirty field tracking
- `stores/execution.js` — Runtime execution state: node statuses, streaming data, per-node log buffers (max 200 entries FIFO)
- `stores/sidebar.js` — Receives `sidebar.tree` events from backend, renders tree directly
- `stores/notifications.js` — Notification bell state: items, unread count, dropdown, pagination (fetchList/loadMore), mark read via backend
- `stores/files.js` — File upload progress tracking: per-upload state, real-time progress (received/total), cancel, clear completed
- `stores/connection.js` — WS connection status: service states (ts_bot, backend, pipeline)
- `stores/presets.js` — LLM/TTS/OCR/VAD/TS preset management: platform+model CRUD per category
- `stores/sttPresets.js` — STT-specific preset management (separate store due to different structure)
- `stores/sysvars.js` — System variables CRUD with optimistic updates, real-time WS sync
- `api/pipeline.js` — `PipelineSocket` class: envelope protocol, promise-based ACK tracking (15s timeout), binary frame upload, heartbeat (30s ping/90s pong), exponential backoff reconnect (3s initial, 30s max)

### Frontend component system
- `components/pipeline/NodeCard.vue` — Glassmorphism node card with ports, tabs, workflow badge
- `components/pipeline/IOPort.vue` — Circular port with hover label, connection state classes
- `components/pipeline/CanvasControls.vue` — Zoom/pan + flow view toggles (all/data/event)
- `components/pipeline/NodePalette.vue` — Draggable node palette with categorized types, drag-to-canvas creation
- `components/pipeline/nodes/registry.js` — Lazy-loaded component registry: type → Vue component
- `components/pipeline/nodes/<Type>Node.vue` — Per-type node body components (18 node types, each with a Vue component)
- `components/pipeline/nodes/NodeConfigForm.vue` — Generic config form per node type
- `components/pipeline/nodes/NodeLogView.vue` — Per-node execution log viewer
- `components/pipeline/nodes/NodeIODataView.vue` — Input/output data inspector
- `components/pipeline/nodes/NodeIOMgmt.vue` — IO port visibility management (show/hide on-demand ports)
- `components/layout/AppLayout.vue` — Main layout with sidebar, canvas, and editor integration
- `components/layout/SidebarTreeNode.vue` — Recursive sidebar renderer for flow_ref, group, and action types
- `components/layout/BottomStatusBar.vue` — Service status indicators
- `components/layout/NotificationBell.vue` — Bell icon with badge + dropdown

### UI design system
- Material Design 3 dark theme with glassmorphism (backdrop-filter blur)
- Colors: primary=#adc7ff (blue, data flow), secondary=#4edea3 (green, ready/success), tertiary=#ffb695 (orange, keywords/alerts)
- Fonts: Inter (body), Space Grotesk (code/labels/tabs)
- Full spec: `team-speak-ai/docs/07-设计系统规范.md`

## Configuration

- **Python**: `team-speak-ai/backend/.env` + `config.py` (Pydantic `BaseSettings`, auto-loads `.env`)
- **Java**: `team-speak-bot/src/main/resources/application.properties` → `BridgeConfig.java`
- **Pipelines**: JSON files in `team-speak-ai/backend/data/flows/` (migrated from YAML in `config/pipelines/`)

## Key constraints

- Java bridge requires the bundled JDK at `environment/jdk-17.0.9+9` and Maven at `environment/apache-maven-3.9.9`
- Audio flows are real-time: the Java bridge polls audio queues every 10ms, Python audio buffer has a 2-second speaker timeout
- STT `stt_listen_node` is a persistent background listener node — it subscribes to AudioBus and runs continuously, triggering downstream nodes on keyword detection. Supports loopback mode for audio monitoring.
- Background listener nodes (stt_listen, stt_history) have special lifecycle management: run in async loops with cancel/timeout/error handling
- The LLM is configured for MiniMax's OpenAI-compatible API (`openai_base_url: https://api.minimaxi.com/v1`) with `openai_reasoning_split: True` for separated thinking output
- All AI provider configuration now goes through the presets system (platform + model tiers) rather than direct `.env` values; `.env` only provides global fallbacks
- Frontend uses dark glassmorphism design language — see `team-speak-ai/docs/07-设计系统规范.md`
- Frontend-backend communication uses `/ws` (envelope protocol for all management) and `/ws/teamspeak` (voice bridge relay, independent channel)
- Backend owns all state (node positions, connections, configs); frontend is an editor + renderer only
- Pipeline definitions use JSON (not YAML), persisted to `data/flows/`
- Streaming execution: nodes can implement `execute_stream()` for chunked processing; the engine auto-detects streaming chains via `stream-*` port prefix and pipelines them with async queues
