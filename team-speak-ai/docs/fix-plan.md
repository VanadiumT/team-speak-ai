# TeamSpeak AI 修复计划

> 基于 `docs/` 下的架构规范、WebSocket 协议、UI 风格指南，对前后端进行全面修复。
> 创建时间: 2026-04-30

---

## P0 — 阻断性问题（核心功能无法工作）

### 1. flow.load 协议不匹配
- **文件**: `frontend/src/api/pipeline.js`, `frontend/src/stores/editor.js`
- **问题**: `sendCommand` 等待 `ack` 消息，但 `flow.load` 后端返回 `event` 类型 `flow.loaded`（websocket-protocol.md §4.2）
- **修复**: `editor.js` 中 `loadFlow` 改用 `_waitForEvent('flow.loaded')` 而非 `sendCommand`

### 2. 执行事件不推送到 /ws 客户端
- **文件**: `backend/api/routes/ws_main.py`, `backend/core/pipeline/emitter.py`, `backend/core/pipeline/engine.py`
- **问题**: `handle_pipeline_run` 启动 pipeline 后没有把 WS 客户端订阅到事件流。EventEmitter 发到 `engine._ws_connections`，但 /ws 客户端在 `_flow_subscribers`，两个集合隔离
- **修复**:
  - `ws_main.py` 中 `handle_pipeline_run` 调用 `_subscribe_flow` 将客户端订阅
  - `engine.py` 中 EventEmitter 广播时同时推送到 `engine._flow_subscribers`
  - 或统一订阅机制，将两个集合合并

### 3. 缺失节点运行时类
- **文件**: `backend/core/nodes/ts_input_node.py` (新建), `backend/core/nodes/stt_history_node.py` (新建)
- **问题**: registry.py 注册了 8 种元数据但只有 7 种运行时类。缺少 `ts_input` 和 `stt_history`
- **修复**: 创建两个节点类，注册到 NodeRegistry

### 4. FlowManager 并发安全
- **文件**: `backend/core/flow/manager.py`
- **问题**: `_locks` 定义了但所有 CRUD 方法未使用，load-modify-save 存在竞态
- **修复**: 在所有修改 flow 的方法中加入 `async with self._get_lock(flow_id)`

### 5. dirtyFields 响应式 + node.config null 检查
- **文件**: `frontend/src/stores/editor.js`
- **问题**:
  - `dirtyFields.value.add(nodeId)` 不触发 Vue 响应式
  - `Object.assign(node.config, config)` 当 config 为 undefined 时崩溃
- **修复**: Set 操作改为创建新 Set；node.config 先初始化空对象

---

## P1 — 高优先级（本周修复）

### 6. 详情面板遮挡画布
- **文件**: `frontend/src/components/pipeline/PipelineView.vue`
- **修复**: 监听 `editorStore.selectedNode && editorStore.editMode`，动态添加 `margin-right: 320px`

### 7. SVG 连线不可点击
- **文件**: `frontend/src/components/pipeline/PipelineView.vue`
- **修复**: `.connections-svg` 保持 `pointer-events: none`，但 `.conn-hit-area` 设置 `pointer-events: stroke`

### 8. 连线颜色不响应节点状态
- **文件**: `frontend/src/components/pipeline/PipelineView.vue`
- **修复**: `connectionPaths` computed 直接读取 `executionStore.nodeStatuses` 响应式数据

### 9. NodePalette 拖放无视缩放
- **文件**: `frontend/src/components/pipeline/NodePalette.vue`, `PipelineView.vue`
- **修复**: 从 PipelineView 共享 zoom 值到 NodePalette

### 10. 端口拖动不持久化
- **文件**: `frontend/src/components/pipeline/IOPort.vue`
- **修复**: mouseup 时发送 `port.move` command 到后端

### 11. WebSocket 心跳
- **文件**: `frontend/src/api/pipeline.js`, `backend/api/routes/ws_main.py`
- **修复**: 前端 30s ping 定时器，后端 90s 空闲超时断开（websocket-protocol.md §6.2）

### 12. important_update level 参数无效
- **文件**: `backend/core/nodes/stt_listen_node.py`
- **修复**: `"status"` 改为 `"info"` 或 `"success"`（websocket-protocol.md §4.10）

### 13. listening 状态不在 NodeState 枚举
- **文件**: `backend/core/pipeline/context.py`
- **修复**: `NodeState` 添加 `LISTENING`（websocket-protocol.md §4.5 状态枚举）

### 14. 中文 flow ID slugify 返回 "untitled"
- **文件**: `backend/core/flow/manager.py`
- **修复**: `_slugify` 保留中文字符

### 15. _use_envelope 改为实例级
- **文件**: `backend/core/pipeline/engine.py`
- **修复**: 从全局标志改为 PipelineInstance 属性

### 16. _trigger_downstream 多节点
- **文件**: `backend/core/pipeline/engine.py`
- **修复**: 移除 `return`，遍历所有匹配下游节点

### 17. node.config null 检查
- **文件**: `frontend/src/stores/editor.js`
- **修复**: 已在 P0-5 中覆盖

---

## P2 — 中优先级（两周内）

### 18. 组件裸色值替换为 CSS 变量
### 19. 节点专属 Vue 组件实现
### 20. 连线点击选中
### 21. 缩放中心跟随鼠标
### 22. ActiveTab store 化
### 23. 添加缺失 command handler (notification, port, flow)
### 24. 添加 message size 限制
### 25. 添加 IP 连接数限制
### 26. 补充 requirements.txt (Pillow, numpy)
### 27. 创建 .env 模板
### 28. 步骤号溢出处理
### 29. Emoji 图标替换为 Material Symbols

---

## P3 — 低优先级（后续优化）

### 30. 删除旧 /ws/pipeline 路由
### 31. 重复连接检测
### 32. undo/redo 广播给所有订阅者
### 33. moveNodeLocal 回滚机制
### 34. selection 颜色调整
### 35. 完成态边框透明度修正
