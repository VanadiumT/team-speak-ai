/**
 * Execution Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    connected: false,
  },
}))

import { useExecutionStore } from '../execution'

describe('ExecutionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useExecutionStore()
    expect(store.status).toBe('idle')
    expect(store.executionId).toBeNull()
    expect(store.nodeStatuses).toEqual({})
    expect(store.nodeLogs).toEqual({})
    expect(store.activeLogTab).toBeNull()
  })

  it('getNodeStatus 返回默认值', () => {
    const store = useExecutionStore()
    const s = store.getNodeStatus('nonexist')
    expect(s.status).toBe('pending')
    expect(s.summary).toBe('')
    expect(s.progress).toBeNull()
    expect(s.data).toEqual({})
    expect(s.condition_result).toBeNull()
  })

  it('getNodeLogs 空节点返回空数组', () => {
    const store = useExecutionStore()
    expect(store.getNodeLogs('nonexist')).toEqual([])
  })

  it('getNodeLogCount 空节点返回 0', () => {
    const store = useExecutionStore()
    expect(store.getNodeLogCount('nonexist')).toBe(0)
  })

  it('nodeStatuses 可以被修改', () => {
    const store = useExecutionStore()
    store.nodeStatuses = {
      n1: { status: 'completed', summary: '完成', progress: 1, data: {}, condition_result: null },
    }
    expect(store.getNodeStatus('n1').status).toBe('completed')
  })

  it('nodeLogs 可以被修改', () => {
    const store = useExecutionStore()
    store.nodeLogs = {
      n1: [{ timestamp: '12:00:00', level: 'info', message: '日志', highlight: false }],
    }
    expect(store.getNodeLogs('n1')).toHaveLength(1)
    expect(store.getNodeLogCount('n1')).toBe(1)
  })
})
