/**
 * SysVars Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    sendCommand: vi.fn().mockResolvedValue({}),
    connected: true,
  },
}))

import { useSysVarsStore } from '../sysvars'

describe('SysVarsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useSysVarsStore()
    expect(store.vars).toEqual({})
    expect(store.loading).toBe(false)
    expect(store.error).toBe('')
    expect(store.toast.show).toBe(false)
  })

  it('vars 是响应式的', () => {
    const store = useSysVarsStore()
    store.vars = { key1: 'val1' }
    expect(store.vars.key1).toBe('val1')
  })
})
