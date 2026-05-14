/**
 * PipelineSocket 测试 — 事件系统 + 信封协议
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// PipelineSocket 是 class，直接测试其事件系统
// WebSocket 需要 mock
const mockWs = {
  readyState: 1, // OPEN
  send: vi.fn(),
  close: vi.fn(),
  onopen: null as (() => void) | null,
  onmessage: null as ((e: MessageEvent) => void) | null,
  onclose: null as (() => void) | null,
  onerror: null as ((e: Event) => void) | null,
}

vi.stubGlobal('WebSocket', vi.fn(() => mockWs))
vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid-1234' })

// 动态导入避免模块缓存问题
const { pipelineSocket } = await import('@/api/pipeline')

describe('PipelineSocket 事件系统', () => {
  beforeEach(() => {
    pipelineSocket.disconnect()
    pipelineSocket.handlers.clear()
  })

  it('on 注册事件处理器', () => {
    const handler = vi.fn()
    pipelineSocket.on('test_event', handler)
    pipelineSocket.emit('test_event', { data: 'hello' })
    expect(handler).toHaveBeenCalledWith({ data: 'hello' })
  })

  it('off 移除事件处理器', () => {
    const handler = vi.fn()
    pipelineSocket.on('test_event', handler)
    pipelineSocket.off('test_event', handler)
    pipelineSocket.emit('test_event', { data: 'hello' })
    expect(handler).not.toHaveBeenCalled()
  })

  it('多个处理器注册同一事件', () => {
    const h1 = vi.fn()
    const h2 = vi.fn()
    pipelineSocket.on('evt', h1)
    pipelineSocket.on('evt', h2)
    pipelineSocket.emit('evt', { x: 1 })
    expect(h1).toHaveBeenCalledTimes(1)
    expect(h2).toHaveBeenCalledTimes(1)
  })

  it('on 不重复注册同一处理器', () => {
    const handler = vi.fn()
    pipelineSocket.on('evt', handler)
    pipelineSocket.on('evt', handler)
    pipelineSocket.emit('evt', {})
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('emit 无处理器时不报错', () => {
    expect(() => pipelineSocket.emit('nonexist', {})).not.toThrow()
  })

  it('处理器异常不影响其他处理器', () => {
    const h1 = vi.fn(() => { throw new Error('boom') })
    const h2 = vi.fn()
    pipelineSocket.on('evt', h1)
    pipelineSocket.on('evt', h2)
    pipelineSocket.emit('evt', {})
    expect(h2).toHaveBeenCalledTimes(1)
  })
})

describe('PipelineSocket 连接状态', () => {
  it('初始未连接', () => {
    expect(pipelineSocket.connected).toBe(false)
  })
})

describe('PipelineSocket 消息分发', () => {
  beforeEach(() => {
    pipelineSocket.disconnect()
    pipelineSocket.handlers.clear()
  })

  it('event 类型消息触发对应 action 处理器', () => {
    const handler = vi.fn()
    pipelineSocket.on('node.status_changed', handler)
    // 模拟 _dispatch
    pipelineSocket['_dispatch']({
      msg_id: 'm1',
      flow_id: 'f1',
      type: 'event',
      action: 'node.status_changed',
      params: { node_id: 'n1', status: 'completed' },
      ts: Date.now(),
    })
    expect(handler).toHaveBeenCalledWith({ node_id: 'n1', status: 'completed' })
  })

  it('ack 类型消息 resolve 对应的 pending promise', () => {
    const resolve = vi.fn()
    const reject = vi.fn()
    const timer = setTimeout(() => {}, 1000)
    pipelineSocket._ackResolvers.set('msg_001', { resolve, reject, timer })

    pipelineSocket['_dispatch']({
      msg_id: 'm2',
      flow_id: 'f1',
      type: 'ack',
      action: '',
      params: { result: 'ok' },
      ts: Date.now(),
      ref_msg_id: 'msg_001',
    })

    expect(resolve).toHaveBeenCalledWith({ result: 'ok' })
    expect(pipelineSocket._ackResolvers.has('msg_001')).toBe(false)
    clearTimeout(timer)
  })

  it('error 类型消息 reject 对应的 pending promise', () => {
    const resolve = vi.fn()
    const reject = vi.fn()
    const timer = setTimeout(() => {}, 1000)
    pipelineSocket._ackResolvers.set('msg_002', { resolve, reject, timer })

    pipelineSocket['_dispatch']({
      msg_id: 'm3',
      flow_id: 'f1',
      type: 'error',
      action: '',
      params: { message: '出错了' },
      ts: Date.now(),
      ref_msg_id: 'msg_002',
    })

    expect(reject).toHaveBeenCalledWith(expect.objectContaining({ message: '出错了' }))
    clearTimeout(timer)
  })
})

describe('PipelineSocket sendCommand', () => {
  it('未连接时 reject', async () => {
    pipelineSocket._connected = false
    await expect(pipelineSocket.sendCommand('f1', 'test', {}))
      .rejects.toThrow('Not connected')
  })
})
