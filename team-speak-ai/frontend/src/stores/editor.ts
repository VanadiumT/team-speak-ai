/**
 * Editor Store — 流程编辑状态
 *
 * 管理节点、连线、撤销/重做、拖拽、配置更新（含 debounce）。
 * 坐标由后端持有，前端仅在 dragend 时发送 node.move。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline'
import { useNotificationsStore } from '@/stores/notifications'
import type {
  NodeDefinition, ConnectionDef, NodeTypeDef, PortDef, NodePosition,
  FlowDefinition, FlowSummary, HistoryState,
} from '@/types/pipeline'

// ── 节点宽度常量（全局统一，供 editor / PipelineView / NodeCard 共用）──
export const NODE_W: Record<string, number> = { input_image: 220, ocr: 220, tts: 250, ts_output: 220, ts_input: 220, vad: 220, context_build: 250, llm: 250, stt_history: 280, stt_listen: 280, start: 220, flow_var_read: 220, flow_var_write: 240, sys_var_read: 220, sys_var_write: 240, display_text: 240 }

export const useEditorStore = defineStore('editor', () => {
  // ── 状态 ──
  const flowId = ref<string | null>(null)
  const flowMeta = ref<Record<string, unknown>>({})          // name, group, icon, skill_prompt, canvas
  const nodes = ref<NodeDefinition[]>([])
  const connections = ref<ConnectionDef[]>([])
  const nodeTypes = ref<NodeTypeDef[]>([])
  const canUndo = ref(false)
  const canRedo = ref(false)
  const isReadOnly = ref(false)     // pipeline 运行时只读
  const editMode = ref(false)       // 编辑模式（默认流程模式）
  const dirtyFields = ref<Set<string>>(new Set()) // 待保存的字段
  const flowParams = ref<Record<string, unknown>>({})
  const selectedNodeId = ref<string | null>(null)
  // Monotonic version counter for optimistic mutations.
  // Server event handlers bump it so that a late rollback from a failed send
  // won't overwrite state that was already corrected by a concurrent WS event.
  const _localVersion = ref(0)

  // 节点内部配置字段（_port_positions, _repeatable_ports, _port_labels 等）
  // 这些字段存储在 node.config 中但不是用户配置，而是编辑器内部状态
  interface NodeConfigInternals {
    _port_positions?: Record<string, { side: string; top: number }>
    _repeatable_ports?: Record<string, string[]>
    _port_labels?: Record<string, string>
    [key: string]: unknown
  }

  // ── 计算属性 ──
  const BASE_CANVAS = { width: 2000, height: 1500 }
  const CANVAS_PAD = 400

  const canvasSize = computed(() => {
    let w = BASE_CANVAS.width, h = BASE_CANVAS.height
    for (const node of nodes.value) {
      const nw = (NODE_W[node.type] || 250) + CANVAS_PAD
      const nh = 200 + CANVAS_PAD
      if (node.position.x + nw > w) w = node.position.x + nw
      if (node.position.y + nh > h) h = node.position.y + nh
    }
    return { width: Math.max(w, 800), height: Math.max(h, 600) }
  })

  // ── 模式切换 ──
  function enterEditMode(): void {
    editMode.value = true
  }

  function exitEditMode(): void {
    editMode.value = false
  }

  // ── 流程加载 ──
  async function loadFlow(id: string): Promise<void> {
    flowId.value = id
    pipelineSocket.activeFlowId = id
    pipelineSocket.sendCommand(id, 'flow.load', {})
    await pipelineSocket._waitForEvent('flow.loaded', 15000)
  }

  function onFlowLoaded({ flow }: { flow: FlowDefinition }): void {
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

    // 同步拉取该流程的通知列表
    useNotificationsStore().fetchList(flow.id)
  }

  function onFlowDeleted({ flow_id }: { flow_id: string }): void {
    if (flowId.value === flow_id) {
      flowId.value = null
      pipelineSocket.activeFlowId = null
      nodes.value = []
      connections.value = []
    }
  }

  // ── 节点操作 ──
  async function createNode(nodeType: string, position: NodePosition = { x: 100, y: 100 }): Promise<boolean> {
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

  function onNodeCreated({ node }: { node: NodeDefinition }): void {
    _localVersion.value++
    nodes.value.push(node)
  }

  async function deleteNode(nodeId: string): Promise<void> {
    const flow = flowId.value
    if (!flow) return
    await pipelineSocket.sendCommand(flow, 'node.delete', { node_id: nodeId })
  }

  function onNodeDeleted({ node_id }: { node_id: string }): void {
    _localVersion.value++
    nodes.value = nodes.value.filter((n) => n.id !== node_id)
    if (selectedNodeId.value === node_id) selectedNodeId.value = null
  }

  async function renameNode(nodeId: string, name: string): Promise<void> {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const node = nodes.value.find((n) => n.id === nodeId)
    if (!node) return
    const prevName = node.name
    const version = ++_localVersion.value
    node.name = name
    try {
      await pipelineSocket.sendCommand(flow, 'node.rename', { node_id: nodeId, name })
    } catch (_) {
      if (_localVersion.value === version) node.name = prevName
    }
  }

  function onNodeRenamed({ node_id, name }: { node_id: string; name: string }): void {
    _localVersion.value++
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) node.name = name
  }

  async function duplicateNode(nodeId: string): Promise<void> {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const source = nodes.value.find((n) => n.id === nodeId)
    if (!source) return
    const offsetPos: NodePosition = {
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

  function moveNodeLocal(nodeId: string, x: number, y: number): void {
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) {
      node.position = { x, y }
    }
  }

  async function commitMoveNode(nodeId: string): Promise<void> {
    const flow = flowId.value
    if (!flow) return
    const node = nodes.value.find((n) => n.id === nodeId)
    if (!node) return
    await pipelineSocket.sendCommand(flow, 'node.move', {
      node_id: nodeId,
      position: node.position,
    })
  }

  function onNodeMoved({ node_id, position }: { node_id: string; position: NodePosition }): void {
    _localVersion.value++
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) {
      node.position = position
    }
  }

  function _applyConfigLocal(nodeId: string, config: Record<string, unknown>): void {
    const idx = nodes.value.findIndex((n) => n.id === nodeId)
    if (idx < 0) return
    const node = nodes.value[idx]
    nodes.value[idx] = { ...node, config: { ...(node.config || {}), ...config } }
  }

  async function updateConfigImmediate(nodeId: string, config: Record<string, unknown>): Promise<void> {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const node = nodes.value.find((n) => n.id === nodeId)
    const prevConfig = node ? { ...(node.config || {}) } : null
    const prevDirty = new Set(dirtyFields.value)
    const version = ++_localVersion.value
    _applyConfigLocal(nodeId, config)
    dirtyFields.value = new Set(dirtyFields.value).add(nodeId)
    try {
      await pipelineSocket.sendCommand(flow, 'node.update_config', {
        node_id: nodeId,
        config,
      })
    } catch (_) {
      if (_localVersion.value === version && node && prevConfig) {
        node.config = prevConfig
        dirtyFields.value = prevDirty
      }
    }
  }

  const _debounceTimers: Record<string, ReturnType<typeof setTimeout>> = {}
  function updateConfigDebounced(nodeId: string, config: Record<string, unknown>): void {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const node = nodes.value.find((n) => n.id === nodeId)
    const preSnapshot = node ? { ...(node.config || {}) } : {}
    _applyConfigLocal(nodeId, config)
    dirtyFields.value = new Set(dirtyFields.value).add(nodeId)

    const key = nodeId
    if (_debounceTimers[key]) clearTimeout(_debounceTimers[key])
    _debounceTimers[key] = setTimeout(async () => {
      dirtyFields.value = new Set([...dirtyFields.value].filter(id => id !== nodeId))
      const prevDirty = new Set(dirtyFields.value)
      const version = ++_localVersion.value
      try {
        await pipelineSocket.sendCommand(flow, 'node.update_config', {
          node_id: nodeId,
          config,
        })
      } catch (_) {
        if (_localVersion.value === version) {
          const target = nodes.value.find((n) => n.id === nodeId)
          if (target) {
            target.config = { ...(target.config || {}), ...preSnapshot }
            dirtyFields.value = prevDirty
          }
        }
      }
    }, 500)
  }

  function onNodeConfigUpdated({ node_id, config }: { node_id: string; config: Record<string, unknown> }): void {
    _localVersion.value++
    const node = nodes.value.find((n) => n.id === node_id)
    if (node) {
      node.config = node.config || {}
      Object.assign(node.config, config)
      dirtyFields.value = new Set([...dirtyFields.value].filter(id => id !== node_id))
    }
  }

  // ── 连线操作 ──
  async function createConnection(fromNode: string, fromPort: string, toNode: string, toPort: string, type: 'data' | 'event' = 'data'): Promise<void> {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const tempId = 'conn_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7)
    const tempConn: ConnectionDef = { id: tempId, from_node: fromNode, from_port: fromPort, to_node: toNode, to_port: toPort, type }
    const version = ++_localVersion.value
    connections.value = [...connections.value, tempConn]
    try {
      await pipelineSocket.sendCommand(flow, 'connection.create', {
        from_node: fromNode, from_port: fromPort,
        to_node: toNode, to_port: toPort, type,
      })
    } catch (_) {
      if (_localVersion.value === version) {
        connections.value = connections.value.filter((c) => c.id !== tempId)
      }
    }
  }

  function onConnectionCreated({ connection }: { connection: ConnectionDef }): void {
    _localVersion.value++
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

  async function deleteConnection(connId: string): Promise<void> {
    const flow = flowId.value
    if (!flow || isReadOnly.value) return
    const prev = [...connections.value]
    const version = ++_localVersion.value
    connections.value = connections.value.filter((c) => c.id !== connId)
    try {
      await pipelineSocket.sendCommand(flow, 'connection.delete', { connection_id: connId })
    } catch (_) {
      if (_localVersion.value === version) {
        connections.value = prev
      }
    }
  }

  function onConnectionDeleted({ connection_id }: { connection_id: string }): void {
    _localVersion.value++
    connections.value = connections.value.filter((c) => c.id !== connection_id)
  }

  // ── 端口操作 ──
  function onPortMoved({ node_id, port_id, side, position }: { node_id: string; port_id: string; side: string; position: number }): void {
    const node = nodes.value.find((n) => n.id === node_id)
    if (!node) return
    if (!node.config) node.config = {}
    const cfg = node.config as NodeConfigInternals
    if (!cfg._port_positions) cfg._port_positions = {}
    cfg._port_positions[port_id] = { side, top: position }
  }

  // ── 动态可重复端口 ──
  function _ensureRepeatablePorts(node: NodeDefinition, group: string): PortDef | null {
    const tdef = getNodeTypeDef(node.type)
    if (!tdef) return null
    const tpl = tdef.ports?.inputs?.find(p => p.repeatable && p.group === group) ||
                tdef.ports?.outputs?.find(p => p.repeatable && p.group === group)
    return tpl || null
  }

  function addRepeatablePort(nodeId: string, group: string): void {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node || isReadOnly.value) return
    const tpl = _ensureRepeatablePorts(node, group)
    if (!tpl) return
    if (!node.config) node.config = {}
    const cfg = node.config as NodeConfigInternals
    if (!cfg._repeatable_ports) cfg._repeatable_ports = {}
    let existing: string[] = cfg._repeatable_ports[group]
    if (!existing) {
      existing = []
      cfg._repeatable_ports[group] = existing
    }
    if (existing.length >= (tpl.max || 20)) return
    const nums = existing.map(id => { const m = id.match(/\d+$/); return m ? parseInt(m[0]) : 0 })
    const nextN = (nums.length > 0 ? Math.max(...nums) : 0) + 1
    const newId = tpl.id.replace(/\d+$/, String(nextN))
    const updated = [...existing, newId]
    cfg._repeatable_ports = { ...cfg._repeatable_ports, [group]: updated }
    if (!cfg._port_labels) cfg._port_labels = {}
    cfg._port_labels[newId] = `${tpl.label}${nextN}`
    if (!cfg._port_positions) cfg._port_positions = {}
    const baseTop = tpl.position?.top || 30
    cfg._port_positions[newId] = { side: tpl.position?.side || 'left', top: baseTop + nextN * 22 }
    updateConfigImmediate(nodeId, {
      _repeatable_ports: cfg._repeatable_ports,
      _port_labels: cfg._port_labels,
      _port_positions: cfg._port_positions,
    })
  }

  function removeRepeatablePort(nodeId: string, portId: string): void {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node || isReadOnly.value) return
    const cfg = (node.config || {}) as NodeConfigInternals
    const groups: Record<string, string[]> = (cfg._repeatable_ports as Record<string, string[]>) || {}
    let foundGroup: string | null = null
    for (const [group, ids] of Object.entries(groups)) {
      if (ids.includes(portId)) { foundGroup = group; break }
    }
    if (!foundGroup) return
    const tpl = _ensureRepeatablePorts(node, foundGroup)
    if (!tpl) return
    const updated = groups[foundGroup].filter(id => id !== portId)
    const minInstances = tpl.min != null ? tpl.min : 1
    if (updated.length < minInstances) return
    const affectedConns = connections.value.filter(c =>
      (c.from_node === nodeId && c.from_port === portId) ||
      (c.to_node === nodeId && c.to_port === portId))
    connections.value = connections.value.filter(c => !affectedConns.includes(c))
    for (const conn of affectedConns) {
      deleteConnection(conn.id)
    }
    const newGroups = { ...groups, [foundGroup]: updated }
    const newLabels = { ...((cfg._port_labels || {}) as Record<string, string>) }
    delete newLabels[portId]
    if (!node.config) node.config = {}
    const cfg2 = node.config as NodeConfigInternals
    cfg2._repeatable_ports = newGroups
    cfg2._port_labels = newLabels
    updateConfigImmediate(nodeId, {
      _repeatable_ports: newGroups,
      _port_labels: newLabels,
    })
  }

  function renamePortLabel(nodeId: string, portId: string, label: string): void {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node || isReadOnly.value) return
    if (!node.config) node.config = {}
    const cfg = node.config as NodeConfigInternals
    if (!cfg._port_labels) cfg._port_labels = {}
    cfg._port_labels = { ...(cfg._port_labels || {}), [portId]: label }
    updateConfigImmediate(nodeId, {
      _port_labels: cfg._port_labels,
    })
  }

  function getNodeTypeDef(nodeType: string): NodeTypeDef | undefined {
    return nodeTypes.value.find((t) => t.type === nodeType)
  }

  function getPortDef(node: NodeDefinition, portId: string, side: 'input' | 'output'): PortDef | null {
    const tdef = getNodeTypeDef(node.type)
    if (!tdef) return null
    const cfg = (node.config || {}) as NodeConfigInternals
    if (cfg._repeatable_ports) {
      for (const [group, ids] of Object.entries(cfg._repeatable_ports as Record<string, string[]>)) {
        if (ids.includes(portId)) {
          const ports = side === 'input' ? tdef.ports?.inputs : tdef.ports?.outputs
          const tpl = ports?.find(p => p.repeatable && p.group === group)
          if (tpl) return { ...tpl, id: portId, label: ((cfg._port_labels as Record<string, string>)?.[portId]) || tpl.label }
        }
      }
    }
    const ports = side === 'input' ? tdef.ports?.inputs : tdef.ports?.outputs
    return ports?.find((p) => p.id === portId) || null
  }

  const COMPATIBLE: Record<string, string[]> = {
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

  function arePortsCompatible(fromNodeId: string, fromPortId: string, toNodeId: string, toPortId: string): boolean {
    const fromNode = nodes.value.find((n) => n.id === fromNodeId)
    const toNode = nodes.value.find((n) => n.id === toNodeId)
    if (!fromNode || !toNode) return false

    const fromPort = getPortDef(fromNode, fromPortId, 'output')
    const toPort = getPortDef(toNode, toPortId, 'input')
    if (!fromPort || !toPort) return false

    const compat = COMPATIBLE[fromPort.data_type]
    if (!compat) return true
    return compat.includes(toPort.data_type)
  }

  // ── 撤销/重做 ──
  async function undo(): Promise<void> {
    const flow = flowId.value
    if (!flow || !canUndo.value) return
    await pipelineSocket.sendCommand(flow, 'undo', {})
  }

  async function redo(): Promise<void> {
    const flow = flowId.value
    if (!flow || !canRedo.value) return
    await pipelineSocket.sendCommand(flow, 'redo', {})
  }

  function onHistoryState({ can_undo, can_redo }: HistoryState): void {
    canUndo.value = can_undo
    canRedo.value = can_redo
  }

  // ── Pipeline 执行锁 ──
  function onPipelineStarted(): void {
    isReadOnly.value = true
  }

  function onPipelineCompleted(): void {
    isReadOnly.value = false
  }

  function onPipelineStopped(): void {
    isReadOnly.value = false
  }

  // ── 工作流管理 ──
  async function createFlow(name: string, group: string, icon: string): Promise<void> {
    await pipelineSocket.sendCommand('_system', 'flow.create', { name, group, icon })
  }

  // ── 初始化 ──
  let _initialized = false
  function init(): void {
    if (_initialized) return
    _initialized = true

    pipelineSocket.on('node_types', (params: Record<string, unknown>) => {
      nodeTypes.value = (params.types as NodeTypeDef[]) || []
    })

    pipelineSocket.on('flow.loaded', onFlowLoaded as (p: Record<string, unknown>) => void)
    pipelineSocket.on('flow.deleted', onFlowDeleted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('node.created', onNodeCreated as (p: Record<string, unknown>) => void)
    pipelineSocket.on('node.deleted', onNodeDeleted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('node.moved', onNodeMoved as (p: Record<string, unknown>) => void)
    pipelineSocket.on('node.renamed', onNodeRenamed as (p: Record<string, unknown>) => void)
    pipelineSocket.on('node.config_updated', onNodeConfigUpdated as (p: Record<string, unknown>) => void)
    pipelineSocket.on('connection.created', onConnectionCreated as (p: Record<string, unknown>) => void)
    pipelineSocket.on('connection.deleted', onConnectionDeleted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('history.state', (p: Record<string, unknown>) => onHistoryState(p as unknown as HistoryState))
    pipelineSocket.on('port.moved', onPortMoved as (p: Record<string, unknown>) => void)
    pipelineSocket.on('pipeline.started', onPipelineStarted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('pipeline.completed', onPipelineCompleted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('pipeline.stopped', onPipelineStopped as (p: Record<string, unknown>) => void)
    pipelineSocket.on('flow.params_updated', onFlowParamsUpdated as (p: Record<string, unknown>) => void)
  }

  function flushPendingUpdates(): void {
    Object.values(_debounceTimers).forEach((t) => clearTimeout(t))
    for (const key of Object.keys(_debounceTimers)) {
      delete _debounceTimers[key]
    }
  }

  // ── 流程参数 ──

  async function updateFlowParams(params: Record<string, unknown>): Promise<void> {
    flowParams.value = { ...flowParams.value, ...params }
    await pipelineSocket.sendCommand(flowId.value!, 'flow.update', { params })
  }

  async function deleteFlowParam(key: string): Promise<void> {
    const { [key]: _, ...rest } = flowParams.value
    flowParams.value = rest
    await pipelineSocket.sendCommand(flowId.value!, 'flow.update', { delete_param: key })
  }

  function onFlowParamsUpdated({ flow_id, params }: { flow_id: string; params: Record<string, unknown> }): void {
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
