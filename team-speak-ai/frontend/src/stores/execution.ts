/**
 * Execution Store — 运行时执行状态
 *
 * 管理 pipeline 执行过程中的节点状态、流式数据、实时日志。
 * 日志缓冲区上限 200 条 FIFO，默认显示最新 50 条。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pipelineSocket } from '@/api/pipeline'

const MAX_LOG_ENTRIES = 200
const DEFAULT_LOG_DISPLAY = 50

interface NodeStatusInfo {
  status: string
  summary: string
  progress: number | null
  data: Record<string, unknown>
  condition_result: string | null
}

interface LogEntry {
  timestamp: string
  level: string
  message: string
  highlight: boolean
}

export const useExecutionStore = defineStore('execution', () => {
  const executionId = ref<string | null>(null)
  const status = ref<string>('idle')
  const nodeStatuses = ref<Record<string, NodeStatusInfo>>({})
  const nodeLogs = ref<Record<string, LogEntry[]>>({})
  const activeLogTab = ref<string | null>(null)

  function getNodeStatus(nodeId: string): NodeStatusInfo {
    return nodeStatuses.value[nodeId] || { status: 'pending', summary: '', progress: null, data: {}, condition_result: null }
  }

  function getNodeLogs(nodeId: string, limit: number = DEFAULT_LOG_DISPLAY): LogEntry[] {
    const logs = nodeLogs.value[nodeId] || []
    if (!limit) return logs
    return logs.slice(-limit)
  }

  function getNodeLogCount(nodeId: string): number {
    return (nodeLogs.value[nodeId] || []).length
  }

  function onPipelineStarted({ execution_id }: { execution_id: string }): void {
    executionId.value = execution_id
    status.value = 'running'
    nodeStatuses.value = {}
    nodeLogs.value = {}
  }

  function onPipelineCompleted(): void {
    status.value = 'completed'
  }

  function onPipelineStopped(): void {
    status.value = 'idle'
  }

  function onNodeStatusChanged({ node_id, status: nodeStatus, summary, progress, data, condition_result }: Record<string, unknown>): void {
    nodeStatuses.value[node_id as string] = {
      status: nodeStatus as string,
      summary: (summary as string) || '',
      progress: (progress as number) ?? null,
      data: (data as Record<string, unknown>) || {},
      condition_result: (condition_result as string) || null,
    }
  }

  function onNodeLogEntry({ node_id, timestamp, level, message, highlight }: Record<string, unknown>): void {
    const id = node_id as string
    if (!nodeLogs.value[id]) {
      nodeLogs.value[id] = []
    }
    const log: LogEntry = {
      timestamp: timestamp as string,
      level: level as string,
      message: message as string,
      highlight: !!highlight,
    }
    nodeLogs.value[id].push(log)

    if (nodeLogs.value[id].length > MAX_LOG_ENTRIES) {
      nodeLogs.value[id] = nodeLogs.value[id].slice(-MAX_LOG_ENTRIES)
    }
  }

  let _initialized = false
  function init(): void {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('pipeline.started', onPipelineStarted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('pipeline.completed', onPipelineCompleted as (p: Record<string, unknown>) => void)
    pipelineSocket.on('pipeline.stopped', onPipelineStopped as (p: Record<string, unknown>) => void)
    pipelineSocket.on('node.status_changed', onNodeStatusChanged)
    pipelineSocket.on('node.log_entry', onNodeLogEntry)
  }

  return {
    executionId, status, nodeStatuses, nodeLogs, activeLogTab,
    getNodeStatus, getNodeLogs, getNodeLogCount,
    init,
  }
})
