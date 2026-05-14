/**
 * Connection Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    connected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendCommand: vi.fn(),
  },
}))

import { useConnectionStore } from '../connection'

describe('ConnectionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useConnectionStore()
    expect(store.isConnected).toBe(false)
    expect(store.services).toEqual([])
    expect(store.reconnectAttempts).toBe(0)
    expect(store.tsBotStatus).toBe('unknown')
    expect(store.backendStatus).toBe('unknown')
    expect(store.pipelineStatus).toBe('unknown')
  })

  it('services 可以被修改', () => {
    const store = useConnectionStore()
    store.services = [
      { id: 'ts_bot', name: 'TS Bot', status: 'connected', detail: '' },
    ]
    expect(store.tsBotStatus).toBe('connected')
  })
})
