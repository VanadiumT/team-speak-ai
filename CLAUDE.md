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
- **Java ↔ Python**: WebSocket `ws://localhost:8080/teamspeak/voice`. Java is the server, Python connects as client via `api/routes/ws_teamspeak.py`. This is an **internal audio bridge** — the frontend does NOT connect to it directly.
- **Python ↔ Frontend**: Single unified WebSocket `ws://localhost:8000/ws` using the **envelope protocol** defined in `docs/websocket-protocol.md`. All flow management, node editing, file upload, execution control, notifications go through this one endpoint.

### Protocol (envelope format)
All messages on `/ws` use a unified envelope: `{msg_id, flow_id, type, action, params, ts}`. See `team-speak-ai/docs/websocket-protocol.md` for the full spec and `team-speak-ai/docs/architecture-spec.md` for the architecture rules.

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

Key files:
- `definition.py` — `NodeTypeDef`, `PortDef`, `PortsDef`, `TabDef`, `NodeDefinition`, `PipelineDefinition`, `ConnectionDef`, `FlowSummary`, `InputMapping`, `TriggerConfig` data classes
- `registry.py` — `NodeRegistry`: `@register_node()` decorator for node class registration, `list_type_defs()` returns full type metadata (ports, tabs, colors) for frontend
- `engine.py` — `PipelineEngine` singleton: loads flows, manages instances, executes nodes, handles WS subscriptions
- `emitter.py` — `EventEmitter`: pushes real-time events (`node.status_changed`, `node.log_entry`, `pipeline.started/completed`) to subscribed WS clients
- `context.py` — `NodeContext`, `NodeOutput`, `NodeState`, `NodeRuntime`

Nodes live in `core/nodes/`. Each node extends `BaseNode` and implements `execute(context, emit) -> NodeOutput`. Nodes are registered via `@NodeRegistry.register("node_name")` and imported in `core/nodes/__init__.py`.

Available node types:
- `input_image` — Image input node
- `ocr` — OCR text extraction
- `ts_input` — TeamSpeak audio input source (subscribes to AudioBus)
- `stt_listen` — STT with keyword detection (persistent background node)
- `stt_history` — STT history + keyword trigger (maintains history window, detects keywords)
- `context_build` — Context builder for LLM
- `llm` — LLM inference node
- `tts` — Text-to-speech output
- `ts_output` — TeamSpeak audio output

### Flow management (`core/flow/`)
- `manager.py` — `FlowManager`: CRUD for flow JSON files, sidebar tree generation, node/connection position persistence, DAG cycle detection, port validation, group hierarchy persistence (`groups.json`), ZIP export/import for groups

### History / undo-redo (`core/history/`)
- `manager.py` — `HistoryManager`: per-flow undo/redo stacks (max 100 entries each), JSONL persistence, 500ms merge window for config updates

### Default config (`core/config/`)
- `defaults.py` — `ConfigDefaultsManager`: load/save per-node-type default configs from `data/defaults/`

### File upload (`core/upload/`)
- `chunk_receiver.py` — `ChunkReceiver`: binary frame file upload with resume support, 256KB chunks, magic byte validation

### Audio bus (`core/audio/`)
- `audio_bus.py` — publish/subscribe bus: `ws_teamspeak.py` publishes incoming audio, `stt_listen_node` consumes it
- `audio_buffer.py` — per-speaker audio buffering with timeout and voice activity detection

### Provider factories
Each AI capability has a factory pattern with swappable backends configured via `config.py` / `.env`:

| Capability | Config key | Available providers | Code path |
|-----------|------------|-------------------|-----------|
| STT | `stt_provider` | `sensevoice` (default), `whisper`, `minimax` | `core/stt/factory.py` |
| TTS | `tts_provider` | `edge` (default), `minimax` | `core/tts/factory.py` |
| LLM | `llm_provider` | `openai` (default, points to MiniMax API) | `core/llm/factory.py` |
| OCR | `ocr_provider` | `easyocr` (default), `paddleocr` | `core/ocr/factory.py` |

### Data persistence
```
backend/data/
  flows/         # Flow JSON files (one per flow)
  groups.json    # Directory/group hierarchy persistence
  defaults/      # Per-node-type default configs (node_ocr.json, etc.)
  history/       # Per-flow operation history JSONL (for undo/redo)
  uploads/       # Uploaded files (by upload_id)
```

### Frontend state management
- `stores/editor.js` — Pinia store for flow editing state: nodes, connections, undo/redo, drag-and-drop, debounced config updates, edit mode toggle, dirty field tracking
- `stores/execution.js` — Runtime execution state: node statuses, streaming data, per-node log buffers (max 200 entries FIFO)
- `stores/sidebar.js` — Receives `sidebar.tree` events from backend, renders tree directly
- `stores/notifications.js` — Notification bell state: items, unread count, dropdown
- `stores/connection.js` — WS connection status: service states (ts_bot, backend, pipeline)
- `api/pipeline.js` — `PipelineSocket` class: envelope protocol, binary frame upload, auto-reconnect with state recovery

### Frontend component system
- `components/pipeline/NodeCard.vue` — Glassmorphism node card with ports, tabs, workflow badge
- `components/pipeline/IOPort.vue` — Circular port with hover label, connection state classes
- `components/pipeline/CanvasControls.vue` — Zoom/pan + flow view toggles (all/data/event)
- `components/pipeline/NodePalette.vue` — Draggable node palette with categorized types, drag-to-canvas creation
- `components/pipeline/nodes/registry.js` — Lazy-loaded component registry: type → Vue component
- `components/pipeline/nodes/<Type>Node.vue` — Per-type node body components
- `components/layout/AppLayout.vue` — Main layout with sidebar, canvas, and editor integration
- `components/layout/SidebarTreeNode.vue` — Recursive sidebar renderer for flow_ref, group, and action types
- `components/layout/BottomStatusBar.vue` — Service status indicators
- `components/layout/NotificationBell.vue` — Bell icon with badge + dropdown

### UI design system
- Material Design 3 dark theme with glassmorphism (backdrop-filter blur)
- Colors: primary=#adc7ff (blue, data flow), secondary=#4edea3 (green, ready/success), tertiary=#ffb695 (orange, keywords/alerts)
- Fonts: Inter (body), Space Grotesk (code/labels/tabs)
- Full spec: `team-speak-ai/docs/ui-style-guide.md`

## Configuration

- **Python**: `team-speak-ai/backend/.env` + `config.py` (Pydantic `BaseSettings`, auto-loads `.env`)
- **Java**: `team-speak-bot/src/main/resources/application.properties` → `BridgeConfig.java`
- **Pipelines**: JSON files in `team-speak-ai/backend/data/flows/` (migrated from YAML in `config/pipelines/`)

## Key constraints

- Java bridge requires the bundled JDK at `environment/jdk-17.0.9+9` and Maven at `environment/apache-maven-3.9.9`
- Audio flows are real-time: the Java bridge polls audio queues every 10ms, Python audio buffer has a 2-second speaker timeout
- STT `stt_listen_node` is a persistent background node — it subscribes to AudioBus and runs continuously, triggering downstream nodes on keyword detection
- The LLM is configured for MiniMax's OpenAI-compatible API (`openai_base_url: https://api.minimaxi.com/v1`) with `openai_reasoning_split: True` for separated thinking output
- Frontend uses dark glassmorphism design language — see `docs/ui-style-guide.md` and `frontend/docs/pipeline-prototype.html`
- All frontend-backend communication goes through a single `/ws` WebSocket using the envelope protocol
- Backend owns all state (node positions, connections, configs); frontend is an editor + renderer only
- Pipeline definitions use JSON (not YAML), persisted to `data/flows/`
