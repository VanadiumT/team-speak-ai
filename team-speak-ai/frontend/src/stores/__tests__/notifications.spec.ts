/**
 * Notifications Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    sendCommand: vi.fn(),
    connected: false,
  },
}))

import { useNotificationsStore } from '../notifications'

describe('NotificationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useNotificationsStore()
    expect(store.items).toEqual([])
    expect(store.unread).toBe(0)
    expect(store.isOpen).toBe(false)
    expect(store.hasUnread).toBe(false)
    expect(store.hasMore).toBe(false)
  })

  it('toggle 切换打开状态', () => {
    const store = useNotificationsStore()
    store.toggle()
    expect(store.isOpen).toBe(true)
    store.toggle()
    expect(store.isOpen).toBe(false)
  })

  it('close 关闭下拉', () => {
    const store = useNotificationsStore()
    store.toggle()
    store.close()
    expect(store.isOpen).toBe(false)
  })

  it('hasUnread 响应式', () => {
    const store = useNotificationsStore()
    store.unread = 5
    expect(store.hasUnread).toBe(true)
    store.unread = 0
    expect(store.hasUnread).toBe(false)
  })

  it('items 可以被修改', () => {
    const store = useNotificationsStore()
    store.items = [
      { id: 'n1', title: '标题', content: '内容', level: 'info', node_id: null, timestamp: '', read: false },
    ]
    expect(store.items).toHaveLength(1)
  })
})
