/**
 * 前端类型定义 —— 与后端 core/pipeline/definition.py 对齐
 *
 * 所有 WebSocket 信封协议的数据结构在此统一定义。
 * 修改时需同步后端 Python dataclass。
 */

// ── WebSocket 信封协议 ────────────────────────────────────────

export interface WsEnvelope {
  msg_id: string
  flow_id: string
  type: 'command' | 'event' | 'ack' | 'error'
  action: string
  params: Record<string, unknown>
  ts: number
  ref_msg_id?: string
}

// ── 节点定义 ──────────────────────────────────────────────────

export interface NodePosition {
  x: number
  y: number
}

export interface TriggerConfig {
  type: string
  source_node?: string
  keywords?: string[]
}

export interface InputMapping {
  from_node: string
  as_field: string
  source_field: string
  required?: boolean
}

export interface NodeDefinition {
  id: string
  type: string
  name: string
  position: NodePosition
  config: Record<string, unknown>
  trigger?: TriggerConfig | null
  input_mappings?: InputMapping[]
  listener?: boolean
}

// ── 连线定义 ──────────────────────────────────────────────────

export interface ConnectionDef {
  id: string
  from_node: string
  from_port: string
  to_node: string
  to_port: string
  type: 'data' | 'event'
}

// ── 流程定义 ──────────────────────────────────────────────────

export interface FlowDefinition {
  id: string
  name: string
  group: string
  icon: string
  enabled: boolean
  skill_prompt: string
  canvas: { width: number; height: number }
  params: Record<string, unknown>
  nodes: NodeDefinition[]
  connections: ConnectionDef[]
}

export interface FlowSummary {
  id: string
  name: string
  group: string
  icon: string
  node_count: number
  enabled: boolean
  updated_at: string
}

// ── 节点类型元数据 ────────────────────────────────────────────

export interface PortPosition {
  side: string
  top: number
}

export interface PortDef {
  id: string
  label: string
  data_type: string
  visibility: 'always' | 'on-demand'
  repeatable: boolean
  group?: string
  min?: number
  max?: number
  position: PortPosition
}

export interface TabDef {
  id: string
  label: string
}

export interface NodeTypeDef {
  type: string
  name: string
  icon: string
  color: string
  default_config: Record<string, unknown>
  tabs: TabDef[]
  ports: {
    inputs: PortDef[]
    outputs: PortDef[]
  }
}

// ── 预设系统 ──────────────────────────────────────────────────

export interface PresetModel {
  id: string
  name: string
  is_default: boolean
  [key: string]: unknown
}

export interface PresetPlatform {
  id: string
  name: string
  provider: string
  api_key?: string
  base_url?: string
  models: PresetModel[]
}

export interface PresetData {
  platforms: PresetPlatform[]
}

// ── 侧栏 ─────────────────────────────────────────────────────

export interface SidebarNode {
  id: string
  name: string
  icon: string
  type: string
  flow_id?: string
  enabled?: boolean
  children?: SidebarNode[]
}

// ── 执行状态 ──────────────────────────────────────────────────

export type NodeStatus = 'idle' | 'starting' | 'running' | 'completed' | 'error' | 'cancelled' | 'paused'

export interface NodeRuntimeStatus {
  node_id: string
  status: NodeStatus
  summary?: string
  progress?: number
  data?: Record<string, unknown>
}

// ── 通知 ──────────────────────────────────────────────────────

export interface NotificationItem {
  id: string
  flow_id: string
  title: string
  content: string
  event_type: string
  timestamp: string
  node_id?: string
}

// ── 系统变量 ──────────────────────────────────────────────────

export interface SysVar {
  key: string
  value: unknown
}

// ── 历史记录 ──────────────────────────────────────────────────

export interface HistoryState {
  can_undo: boolean
  can_redo: boolean
}

// ── 服务状态 ──────────────────────────────────────────────────

export interface ServiceStatus {
  id: string
  name: string
  status: 'connected' | 'disconnected' | 'healthy' | 'error'
  detail: string
}
