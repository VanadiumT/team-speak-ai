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

  // ── 计算属性 ──
  const canvasSize = computed(() => flowMeta.value.canvas || { width: 1700, height: 1250 })

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
      canvas: flow.canvas || { width: 1700, height: 1250 },
    }
    nodes.value = flow.nodes || []
    connections.value = flow.connections || []
  }

  function onFlowCreated({ flow }) {}

  function onFlowDeleted({ flow_id }) {
    if (flowId.value === flow_id) {
      flowId.value = null
      nodes.value = []
      connections.value = []
    }
  }

  // ── 节点操作 ──
  async function createNode(nodeType, position = { x: 100, y: 100 }) {
    const flow = flowId.value
    if (!flow) return
    await pipelineSocket.sendCommand(flow, 'node.create', {
      node_type: nodeType,
      position,
    })
  }

  function onNodeCreated({ node }) {
    nodes.value.push(node)
  }

  async function deleteNode(nodeId) {
    const flow = flowId.value
    if (!flow) return
    await pipelineSocket.sendCommand(flow, 'node.delete', { node_id: nodeId })
  }

  function onNodeDeleted({ node_id }) {
    nodes.value = nodes.value.filter((n) => n.id !== node_id)
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

  async function updateConfigImmediate(nodeId, config) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    dirtyFields.value = new Set(dirtyFields.value).add(nodeId)
    await pipelineSocket.sendCommand(flow, 'node.update_config', {
      node_id: nodeId,
      config,
    })
  }

  let _debounceTimers = {}
  function updateConfigDebounced(nodeId, config) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    dirtyFields.value = new Set(dirtyFields.value).add(nodeId)

    const key = nodeId
    if (_debounceTimers[key]) clearTimeout(_debounceTimers[key])
    _debounceTimers[key] = setTimeout(async () => {
      dirtyFields.value.delete(nodeId)
      dirtyFields.value = new Set(dirtyFields.value)
      await pipelineSocket.sendCommand(flow, 'node.update_config', {
        node_id: nodeId,
        config,
      })
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
    await pipelineSocket.sendCommand(flow, 'connection.create', {
      from_node: fromNode,
      from_port: fromPort,
      to_node: toNode,
      to_port: toPort,
      type,
    })
  }

  function onConnectionCreated({ connection }) {
    connections.value.push(connection)
  }

  async function deleteConnection(connId) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    await pipelineSocket.sendCommand(flow, 'connection.delete', { connection_id: connId })
  }

  function onConnectionDeleted({ connection_id }) {
    connections.value = connections.value.filter((c) => c.id !== connection_id)
  }

  // ── 端口操作 ──
  function getNodeTypeDef(nodeType) {
    return nodeTypes.value.find((t) => t.type === nodeType)
  }

  function getPortDef(node, portId, side) {
    const tdef = getNodeTypeDef(node.type)
    if (!tdef) return null
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
      image: ['image'],
      audio: ['audio'],
      string: ['string', 'string_array'],
      string_array: ['string_array', 'messages'],
      messages: ['messages'],
      event: [],
    }
    const compat = COMPATIBLE[fromPort.data_type]
    return compat && compat.includes(toPort.data_type)
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
  function init() {
    pipelineSocket.on('node_types', ({ types }) => {
      nodeTypes.value = types || []
    })

    pipelineSocket.on('flow.loaded', onFlowLoaded)
    pipelineSocket.on('flow.created', onFlowCreated)
    pipelineSocket.on('flow.deleted', onFlowDeleted)
    pipelineSocket.on('node.created', onNodeCreated)
    pipelineSocket.on('node.deleted', onNodeDeleted)
    pipelineSocket.on('node.moved', onNodeMoved)
    pipelineSocket.on('node.config_updated', onNodeConfigUpdated)
    pipelineSocket.on('connection.created', onConnectionCreated)
    pipelineSocket.on('connection.deleted', onConnectionDeleted)
    pipelineSocket.on('history.state', onHistoryState)
    pipelineSocket.on('pipeline.started', onPipelineStarted)
    pipelineSocket.on('pipeline.completed', onPipelineCompleted)
    pipelineSocket.on('pipeline.stopped', onPipelineStopped)
  }

  function flushPendingUpdates() {
    Object.values(_debounceTimers).forEach((t) => clearTimeout(t))
    _debounceTimers = {}
  }

  return {
    flowId, flowMeta, nodes, connections, nodeTypes,
    canUndo, canRedo, isReadOnly, editMode, dirtyFields, canvasSize,
    enterEditMode, exitEditMode,
    loadFlow, createNode, deleteNode, moveNodeLocal, commitMoveNode,
    updateConfigImmediate, updateConfigDebounced,
    createConnection, deleteConnection,
    getNodeTypeDef, getPortDef, arePortsCompatible,
    undo, redo, init, flushPendingUpdates,
    createFlow, onFlowLoaded,
  }
})
