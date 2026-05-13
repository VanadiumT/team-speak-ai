/**
 * Editor Store — 流程编辑状态
 *
 * 管理节点、连线、撤销/重做、拖拽、配置更新（含 debounce）。
 * 坐标由后端持有，前端仅在 dragend 时发送 node.move。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useEditorStore = defineStore('editor', () => {
  // ── 状态 ──
  const flowId = ref(null)
  const flowMeta = ref({})          // name, group, icon, skill_prompt, canvas
  const nodes = ref([])             // NodeDef[]
  const connections = ref([])       // ConnectionDef[]
  const nodeTypes = ref([])         // NodeTypeDef[] (from node_types event)
  const canUndo = ref(false)
  const canRedo = ref(false)
  const isReadOnly = ref(false)     // pipeline 运行时只读
  const editMode = ref(false)       // 编辑模式（默认流程模式）
  const dirtyFields = ref(new Set()) // 待保存的字段（使用新 Set 替换保证响应式）
  const flowParams = ref({})        // 流程参数 (key-value)
  const selectedNodeId = ref(null)  // 当前选中的节点 ID

  // ── 计算属性 ──
  const BASE_CANVAS = { width: 2000, height: 1500 }
  const NODE_W = { input_image: 220, ocr: 220, tts: 250, ts_output: 220, ts_input: 220, vad: 220, context_build: 250, llm: 250, stt_history: 280, stt_listen: 280, start: 220, flow_var_read: 220, flow_var_write: 240, sys_var_read: 220, sys_var_write: 240, display_text: 240 }
  const CANVAS_PAD = 400  // 节点超出后额外留白

  const canvasSize = computed(() => {
    let w = BASE_CANVAS.width, h = BASE_CANVAS.height
    for (const node of nodes.value) {
      const nw = (NODE_W[node.type] || 250) + CANVAS_PAD
      const nh = 200 + CANVAS_PAD  // 估算节点高度 + 留白
      if (node.position.x + nw > w) w = node.position.x + nw
      if (node.position.y + nh > h) h = node.position.y + nh
    }
    return { width: Math.max(w, 800), height: Math.max(h, 600) }
  })

  // ── 模式切换 ──
  function enterEditMode() {
    editMode.value = true
  }

  function exitEditMode() {
    editMode.value = false
  }

  // ── 流程加载 ──
  async function loadFlow(id) {
    flowId.value = id
    pipelineSocket.activeFlowId = id
    // flow.load 返回 event (flow.loaded)，不是 ack，用 _waitForEvent 等待
    pipelineSocket.sendCommand(id, 'flow.load', {})
    await pipelineSocket._waitForEvent('flow.loaded', 15000)
  }

  function onFlowLoaded({ flow }) {
    flowId.value = flow.id
    flowMeta.value = {
      name: flow.name,
      group: flow.group,
      icon: flow.icon,
      skill_prompt: flow.skill_prompt,
      canvas: flow.canvas || { width: 2000, height: 1500 },
    }
    flowParams.value = flow.params || {}
    nodes.value = flow.nodes || []
    connections.value = flow.connections || []
  }

  function onFlowCreated({ flow }) {}

  function onFlowDeleted({ flow_id }) {
    if (flowId.value === flow_id) {
      flowId.value = null
      pipelineSocket.activeFlowId = null
      nodes.value = []
      connections.value = []
    }
  }

  // ── 节点操作 ──
  async function createNode(nodeType, position = { x: 100, y: 100 }) {
    const flow = flowId.value
    if (!flow) {
      console.error('[Editor] createNode: no flow loaded')
      return false
    }
    if (!pipelineSocket.connected) {
      console.error('[Editor] createNode: WebSocket not connected')
      return false
    }
    try {
      await pipelineSocket.sendCommand(flow, 'node.create', {
        node_type: nodeType,
        position,
      })
      return true
    } catch (e) {
      console.error('[Editor] createNode failed:', e)
      return false
    }
  }

  function onNodeCreated({ node }) {
    console.log('[Editor] onNodeCreated — pushing node:', node?.id, 'type:', node?.type, 'pos:', node?.position, 'total before:', nodes.value.length)
    nodes.value.push(node)
    console.log('[Editor] nodes total after push:', nodes.value.length)
  }

  async function deleteNode(nodeId) {
    const flow = flowId.value
    if (!flow) return
    await pipelineSocket.sendCommand(flow, 'node.delete', { node_id: nodeId })
  }

  function onNodeDeleted({ node_id }) {
    nodes.value = nodes.value.filter((n) => n.id !== node_id)
    if (selectedNodeId.value === node_id) selectedNodeId.value = null
  }

  async function renameNode(nodeId, name) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    // Optimistic local update
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) node.name = name
    try {
      await pipelineSocket.sendCommand(flow, 'node.rename', { node_id: nodeId, name })
    } catch (_) { /* server will broadcast corrected state */ }
  }

  function onNodeRenamed({ node_id, name }) {
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) node.name = name
  }

  async function duplicateNode(nodeId) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const source = nodes.value.find((n) => n.id === nodeId)
    if (!source) return
    const offsetPos = {
      x: (source.position.x || 0) + 40,
      y: (source.position.y || 0) + 40,
    }
    try {
      await pipelineSocket.sendCommand(flow, 'node.create', {
        node_type: source.type,
        position: offsetPos,
        config: source.config,
        name: (source.name || source.type) + ' (副本)',
      })
    } catch (e) {
      console.error('[Editor] duplicateNode failed:', e)
    }
  }

  function moveNodeLocal(nodeId, x, y) {
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) {
      node.position = { x, y }
    }
  }

  async function commitMoveNode(nodeId) {
    const flow = flowId.value
    if (!flow) return
    const node = nodes.value.find((n) => n.id === nodeId)
    if (!node) return
    await pipelineSocket.sendCommand(flow, 'node.move', {
      node_id: nodeId,
      position: node.position,
    })
  }

  function onNodeMoved({ node_id, position }) {
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) {
      node.position = position
    }
  }

  function _applyConfigLocal(nodeId, config) {
    const idx = nodes.value.findIndex((n) => n.id === nodeId)
    if (idx < 0) return
    const node = nodes.value[idx]
    nodes.value[idx] = { ...node, config: { ...(node.config || {}), ...config } }
  }

  async function updateConfigImmediate(nodeId, config) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    _applyConfigLocal(nodeId, config)
    dirtyFields.value = new Set(dirtyFields.value).add(nodeId)
    try {
      await pipelineSocket.sendCommand(flow, 'node.update_config', {
        node_id: nodeId,
        config,
      })
    } catch (_) { /* server will broadcast corrected state */ }
  }

  let _debounceTimers = {}
  function updateConfigDebounced(nodeId, config) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    _applyConfigLocal(nodeId, config)
    dirtyFields.value = new Set(dirtyFields.value).add(nodeId)

    const key = nodeId
    if (_debounceTimers[key]) clearTimeout(_debounceTimers[key])
    _debounceTimers[key] = setTimeout(async () => {
      dirtyFields.value = new Set([...dirtyFields.value].filter(id => id !== nodeId))
      try {
        await pipelineSocket.sendCommand(flow, 'node.update_config', {
          node_id: nodeId,
          config,
        })
      } catch (_) { /* server will broadcast corrected state */ }
    }, 500)
  }

  function onNodeConfigUpdated({ node_id, config }) {
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) {
      node.config = node.config || {}
      Object.assign(node.config, config)
      dirtyFields.value = new Set([...dirtyFields.value].filter(id => id !== node_id))
    }
  }

  // ── 连线操作 ──
  async function createConnection(fromNode, fromPort, toNode, toPort, type = 'data') {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    // Optimistic: add a temp connection with generated id
    const tempId = 'conn_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7)
    const tempConn = { id: tempId, from_node: fromNode, from_port: fromPort, to_node: toNode, to_port: toPort, type }
    connections.value = [...connections.value, tempConn]
    try {
      await pipelineSocket.sendCommand(flow, 'connection.create', {
        from_node: fromNode, from_port: fromPort,
        to_node: toNode, to_port: toPort, type,
      })
    } catch (_) {
      // Remove temp on failure; server will broadcast the real one on success
      connections.value = connections.value.filter((c) => c.id !== tempId)
    }
  }

  function onConnectionCreated({ connection }) {
    // Replace temp connection or add new one
    const existing = connections.value.findIndex((c) =>
      c.from_node === connection.from_node && c.from_port === connection.from_port &&
      c.to_node === connection.to_node && c.to_port === connection.to_port &&
      String(c.id).startsWith('conn_'))
    if (existing >= 0) {
      connections.value[existing] = connection
    } else {
      connections.value.push(connection)
    }
  }

  async function deleteConnection(connId) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    // Optimistic removal
    const prev = [...connections.value]
    connections.value = connections.value.filter((c) => c.id !== connId)
    try {
      await pipelineSocket.sendCommand(flow, 'connection.delete', { connection_id: connId })
    } catch (_) {
      connections.value = prev
    }
  }

  function onConnectionDeleted({ connection_id }) {
    connections.value = connections.value.filter((c) => c.id !== connection_id)
  }

  // ── 端口操作 ──
  function onPortMoved({ node_id, port_id, side, position }) {
    const node = nodes.value.find((n) => n.id === node_id)
    if (!node) return
    if (!node.config) node.config = {}
    if (!node.config._port_positions) node.config._port_positions = {}
    node.config._port_positions[port_id] = { side, top: position }
  }

  // ── 动态可重复端口 ──
  function _ensureRepeatablePorts(node, group) {
    const tdef = getNodeTypeDef(node.type)
    if (!tdef) return null
    const tpl = tdef.ports?.inputs?.find(p => p.repeatable && p.group === group) ||
                tdef.ports?.outputs?.find(p => p.repeatable && p.group === group)
    return tpl
  }

  function addRepeatablePort(nodeId, group) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node || isReadOnly.value) return
    const tpl = _ensureRepeatablePorts(node, group)
    if (!tpl) return
    if (!node.config) node.config = {}
    if (!node.config._repeatable_ports) node.config._repeatable_ports = {}
    let existing = node.config._repeatable_ports[group]
    if (!existing) {
      existing = []
      node.config._repeatable_ports[group] = existing
    }
    if (existing.length >= (tpl.max || 20)) return
    // Generate next id: ctx-in{N}
    const nums = existing.map(id => { const m = id.match(/\d+$/); return m ? parseInt(m[0]) : 0 })
    const nextN = (nums.length > 0 ? Math.max(...nums) : 0) + 1
    const newId = tpl.id.replace(/\d+$/, String(nextN))
    const updated = [...existing, newId]
    node.config._repeatable_ports = { ...node.config._repeatable_ports, [group]: updated }
    if (!node.config._port_labels) node.config._port_labels = {}
    node.config._port_labels[newId] = `${tpl.label}${nextN}`
    // Auto-offset position
    if (!node.config._port_positions) node.config._port_positions = {}
    const baseTop = tpl.position?.top || 30
    node.config._port_positions[newId] = { side: tpl.position?.side || 'left', top: baseTop + nextN * 22 }
    updateConfigImmediate(nodeId, {
      _repeatable_ports: node.config._repeatable_ports,
      _port_labels: node.config._port_labels,
      _port_positions: node.config._port_positions,
    })
  }

  function removeRepeatablePort(nodeId, portId) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node || isReadOnly.value) return
    // Find which group this port belongs to
    const groups = node.config?._repeatable_ports || {}
    let foundGroup = null
    for (const [group, ids] of Object.entries(groups)) {
      if (ids.includes(portId)) { foundGroup = group; break }
    }
    if (!foundGroup) return
    const tpl = _ensureRepeatablePorts(node, foundGroup)
    if (!tpl) return
    const updated = groups[foundGroup].filter(id => id !== portId)
    const minInstances = tpl.min != null ? tpl.min : 1
    if (updated.length < minInstances) return
    // Capture affected connections before removing
    const affectedConns = connections.value.filter(c =>
      (c.from_node === nodeId && c.from_port === portId) ||
      (c.to_node === nodeId && c.to_port === portId))
    // Remove connections locally
    connections.value = connections.value.filter(c => !affectedConns.includes(c))
    // Send delete for each removed connection
    for (const conn of affectedConns) {
      deleteConnection(conn.id)
    }
    // Update config
    const newGroups = { ...groups, [foundGroup]: updated }
    const newLabels = { ...(node.config._port_labels || {}) }
    delete newLabels[portId]
    if (!node.config) node.config = {}
    node.config._repeatable_ports = newGroups
    node.config._port_labels = newLabels
    updateConfigImmediate(nodeId, {
      _repeatable_ports: newGroups,
      _port_labels: newLabels,
    })
  }

  function renamePortLabel(nodeId, portId, label) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node || isReadOnly.value) return
    if (!node.config) node.config = {}
    if (!node.config._port_labels) node.config._port_labels = {}
    node.config._port_labels = { ...node.config._port_labels, [portId]: label }
    updateConfigImmediate(nodeId, {
      _port_labels: node.config._port_labels,
    })
  }

  function getNodeTypeDef(nodeType) {
    return nodeTypes.value.find((t) => t.type === nodeType)
  }

  function getPortDef(node, portId, side) {
    const tdef = getNodeTypeDef(node.type)
    if (!tdef) return null
    // Check dynamic repeatable ports first
    if (node.config?._repeatable_ports) {
      for (const [group, ids] of Object.entries(node.config._repeatable_ports)) {
        if (ids.includes(portId)) {
          // Find template port for this group
          const ports = side === 'input' ? tdef.ports?.inputs : tdef.ports?.outputs
          const tpl = ports?.find(p => p.repeatable && p.group === group)
          if (tpl) return { ...tpl, id: portId, label: node.config?._port_labels?.[portId] || tpl.label }
        }
      }
    }
    const ports = side === 'input' ? tdef.ports?.inputs : tdef.ports?.outputs
    return ports?.find((p) => p.id === portId) || null
  }

  function arePortsCompatible(fromNodeId, fromPortId, toNodeId, toPortId) {
    const fromNode = nodes.value.find((n) => n.id === fromNodeId)
    const toNode = nodes.value.find((n) => n.id === toNodeId)
    if (!fromNode || !toNode) return false

    const fromPort = getPortDef(fromNode, fromPortId, 'output')
    const toPort = getPortDef(toNode, toPortId, 'input')
    if (!fromPort || !toPort) return false

    const COMPATIBLE = {
      image: ['image', 'any'],
      audio: ['audio', 'any'],
      string: ['string', 'string_array', 'any'],
      string_array: ['string_array', 'messages', 'any'],
      messages: ['messages', 'any'],
      event: ['event', 'any'],
      any: ['image', 'audio', 'string', 'string_array', 'messages', 'event', 'any'],
      number: ['number', 'any'],
      list: ['list', 'any'],
      dict: ['dict', 'any'],
    }
    const compat = COMPATIBLE[fromPort.data_type]
    if (!compat) return true
    return compat.includes(toPort.data_type)
  }

  // ── 撤销/重做 ──
  async function undo() {
    const flow = flowId.value
    if (!flow || !canUndo.value) return
    await pipelineSocket.sendCommand(flow, 'undo', {})
  }

  async function redo() {
    const flow = flowId.value
    if (!flow || !canRedo.value) return
    await pipelineSocket.sendCommand(flow, 'redo', {})
  }

  function onHistoryState({ can_undo, can_redo }) {
    canUndo.value = can_undo
    canRedo.value = can_redo
  }

  // ── Pipeline 执行锁 ──
  function onPipelineStarted() {
    isReadOnly.value = true
  }

  function onPipelineCompleted() {
    isReadOnly.value = false
  }

  function onPipelineStopped() {
    isReadOnly.value = false
  }

  // ── 工作流管理 ──
  async function createFlow(name, group, icon) {
    await pipelineSocket.sendCommand('_system', 'flow.create', { name, group, icon })
  }

  // ── 初始化 ──
  let _initialized = false
  function init() {
    if (_initialized) return
    _initialized = true

    pipelineSocket.on('node_types', ({ types }) => {
      nodeTypes.value = types || []
    })

    pipelineSocket.on('flow.loaded', onFlowLoaded)
    pipelineSocket.on('flow.created', onFlowCreated)
    pipelineSocket.on('flow.deleted', onFlowDeleted)
    pipelineSocket.on('node.created', onNodeCreated)
    pipelineSocket.on('node.deleted', onNodeDeleted)
    pipelineSocket.on('node.moved', onNodeMoved)
    pipelineSocket.on('node.renamed', onNodeRenamed)
    pipelineSocket.on('node.config_updated', onNodeConfigUpdated)
    pipelineSocket.on('connection.created', onConnectionCreated)
    pipelineSocket.on('connection.deleted', onConnectionDeleted)
    pipelineSocket.on('history.state', onHistoryState)
    pipelineSocket.on('port.moved', onPortMoved)
    pipelineSocket.on('pipeline.started', onPipelineStarted)
    pipelineSocket.on('pipeline.completed', onPipelineCompleted)
    pipelineSocket.on('pipeline.stopped', onPipelineStopped)
    pipelineSocket.on('flow.params_updated', onFlowParamsUpdated)
  }

  function flushPendingUpdates() {
    Object.values(_debounceTimers).forEach((t) => clearTimeout(t))
    _debounceTimers = {}
  }

  // ── 流程参数 ──

  async function updateFlowParams(params) {
    flowParams.value = { ...flowParams.value, ...params }
    await pipelineSocket.sendCommand(flowId.value, 'flow.update', { params })
  }

  async function deleteFlowParam(key) {
    const { [key]: _, ...rest } = flowParams.value
    flowParams.value = rest
    await pipelineSocket.sendCommand(flowId.value, 'flow.update', { delete_param: key })
  }

  function onFlowParamsUpdated({ flow_id, params }) {
    if (flowId.value === flow_id) {
      flowParams.value = params
    }
  }

  return {
    flowId, flowMeta, nodes, connections, nodeTypes,
    canUndo, canRedo, isReadOnly, editMode, dirtyFields, canvasSize, flowParams, selectedNodeId,
    enterEditMode, exitEditMode,
    loadFlow, createNode, deleteNode, duplicateNode, renameNode, moveNodeLocal, commitMoveNode,
    updateConfigImmediate, updateConfigDebounced,
    createConnection, deleteConnection,
    getNodeTypeDef, getPortDef, arePortsCompatible,
    addRepeatablePort, removeRepeatablePort, renamePortLabel,
    undo, redo, init, flushPendingUpdates,
    createFlow, onFlowLoaded,
    updateFlowParams, deleteFlowParam, onFlowParamsUpdated,
  }
})
