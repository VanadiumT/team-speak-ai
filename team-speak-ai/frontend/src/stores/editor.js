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
  const dirtyFields = ref(new Set()) // 待保存的字段

  // ── 计算属性 ──
  const canvasSize = computed(() => flowMeta.value.canvas || { width: 1700, height: 1250 })

  // ── 流程加载 ──

  async function loadFlow(id) {
    flowId.value = id
    const result = await pipelineSocket.sendCommand(id, 'flow.load', { flow_id: id })
    // flow.loaded event will arrive in event handler
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

  function onFlowCreated({ flow }) {
    // 新建流程后，新的 flow 出现在侧栏
  }

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

  // 拖拽过程中乐观更新本地 UI（不发送网络请求）
  function moveNodeLocal(nodeId, x, y) {
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) {
      node.position = { x, y }
    }
  }

  // dragend 时发送最终位置
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

  // 即时控件（switch/toggle/select）：立即发送
  async function updateConfigImmediate(nodeId, config) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    dirtyFields.value.add(nodeId)
    await pipelineSocket.sendCommand(flow, 'node.update_config', {
      node_id: nodeId,
      config,
    })
  }

  // 文本输入：500ms debounce
  let _debounceTimers = {}
  function updateConfigDebounced(nodeId, config) {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    dirtyFields.value.add(nodeId)

    const key = nodeId
    if (_debounceTimers[key]) clearTimeout(_debounceTimers[key])
    _debounceTimers[key] = setTimeout(async () => {
      dirtyFields.value.delete(nodeId)
      await pipelineSocket.sendCommand(flow, 'node.update_config', {
        node_id: nodeId,
        config,
      })
    }, 500)
  }

  function onNodeConfigUpdated({ node_id, config }) {
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) {
      Object.assign(node.config, config)
      dirtyFields.value.delete(node_id)
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

    // 编辑锁
    pipelineSocket.on('pipeline.started', onPipelineStarted)
    pipelineSocket.on('pipeline.completed', onPipelineCompleted)
    pipelineSocket.on('pipeline.stopped', onPipelineStopped)
  }

  // ── 清理 ──

  function flushPendingUpdates() {
    Object.values(_debounceTimers).forEach((t) => clearTimeout(t))
    _debounceTimers = {}
  }

  return {
    flowId, flowMeta, nodes, connections, nodeTypes,
    canUndo, canRedo, isReadOnly, dirtyFields, canvasSize,
    loadFlow, createNode, deleteNode, moveNodeLocal, commitMoveNode,
    updateConfigImmediate, updateConfigDebounced,
    createConnection, deleteConnection,
    undo, redo, init, flushPendingUpdates,
  }
})
