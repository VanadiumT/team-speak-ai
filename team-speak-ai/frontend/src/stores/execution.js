/**
 * Execution Store — 运行时执行状态
 *
 * 管理 pipeline 执行过程中的节点状态、流式数据、实时日志。
 * 日志缓冲区上限 200 条 FIFO，默认显示最新 50 条。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

const MAX_LOG_ENTRIES = 200
const DEFAULT_LOG_DISPLAY = 50

export const useExecutionStore = defineStore('execution', () => {
  // ── 状态 ──
  const executionId = ref(null)
  const status = ref('idle')                // idle | running | completed | error
  const nodeStatuses = ref({})              // node_id → { status, summary, progress, data, condition_result }
  const nodeLogs = ref({})                  // node_id → [{ timestamp, level, message, highlight }]
  const activeLogTab = ref(null)            // 当前查看的节点日志

  // ── 计算属性 ──

  function getNodeStatus(nodeId) {
    return nodeStatuses.value[nodeId] || { status: 'pending', summary: '', progress: null, data: {} }
  }

  function getNodeLogs(nodeId, limit = DEFAULT_LOG_DISPLAY) {
    const logs = nodeLogs.value[nodeId] || []
    return logs.slice(-limit)
  }

  function getNodeLogCount(nodeId) {
    return (nodeLogs.value[nodeId] || []).length
  }

  // ── Pipeline 生命周期 ──

  function onPipelineStarted({ execution_id }) {
    executionId.value = execution_id
    status.value = 'running'
    nodeStatuses.value = {}
    nodeLogs.value = {}
  }

  function onPipelineCompleted() {
    status.value = 'completed'
  }

  function onPipelineStopped() {
    status.value = 'idle'
  }

  // ── 节点状态 ──

  function onNodeStatusChanged({ node_id, status: nodeStatus, summary, progress, data, condition_result }) {
    nodeStatuses.value[node_id] = {
      status: nodeStatus,
      summary: summary || '',
      progress: progress ?? null,
      data: data || {},
      condition_result: condition_result || null,
    }
  }

  // ── 节点日志 ──

  function onNodeLogEntry({ node_id, timestamp, level, message, highlight }) {
    if (!nodeLogs.value[node_id]) {
      nodeLogs.value[node_id] = []
    }
    const log = { timestamp, level, message, highlight: !!highlight }
    nodeLogs.value[node_id].push(log)

    // FIFO 裁剪
    if (nodeLogs.value[node_id].length > MAX_LOG_ENTRIES) {
      nodeLogs.value[node_id] = nodeLogs.value[node_id].slice(-MAX_LOG_ENTRIES)
    }
  }

  // ── 初始化 ──

  function init() {
    pipelineSocket.on('pipeline.started', onPipelineStarted)
    pipelineSocket.on('pipeline.completed', onPipelineCompleted)
    pipelineSocket.on('pipeline.stopped', onPipelineStopped)
    pipelineSocket.on('node.status_changed', onNodeStatusChanged)
    pipelineSocket.on('node.log_entry', onNodeLogEntry)
  }

  return {
    executionId, status, nodeStatuses, nodeLogs, activeLogTab,
    getNodeStatus, getNodeLogs, getNodeLogCount,
    init,
  }
})
