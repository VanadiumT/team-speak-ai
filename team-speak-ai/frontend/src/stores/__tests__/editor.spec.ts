/**
 * Editor Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    sendCommand: vi.fn().mockResolvedValue({}),
    _waitForEvent: vi.fn().mockResolvedValue({}),
    connected: false,
    activeFlowId: null,
    handlers: new Map(),
  },
}))

vi.mock('@/stores/notifications', () => ({
  useNotificationsStore: vi.fn(() => ({
    fetchList: vi.fn(),
    init: vi.fn(),
  })),
}))

import { useEditorStore, NODE_W } from '../editor'

describe('EditorStore 基础状态', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useEditorStore()
    expect(store.flowId).toBeNull()
    expect(store.nodes).toEqual([])
    expect(store.connections).toEqual([])
    expect(store.canUndo).toBe(false)
    expect(store.canRedo).toBe(false)
    expect(store.editMode).toBe(false)
    expect(store.isReadOnly).toBe(false)
  })

  it('enterEditMode / exitEditMode', () => {
    const store = useEditorStore()
    store.enterEditMode()
    expect(store.editMode).toBe(true)
    store.exitEditMode()
    expect(store.editMode).toBe(false)
  })

  it('NODE_W 包含主要节点类型', () => {
    const expected = [
      'start', 'input_image', 'ocr', 'display_text',
      'llm', 'tts', 'stt_listen', 'stt_history', 'vad',
      'context_build', 'ts_input', 'ts_output',
      'flow_var_read', 'flow_var_write', 'sys_var_read', 'sys_var_write',
    ]
    for (const t of expected) {
      expect(NODE_W[t], `NODE_W 缺少 ${t}`).toBeDefined()
    }
  })

  it('NODE_W 值为正数', () => {
    for (const [, v] of Object.entries(NODE_W)) {
      expect(v).toBeGreaterThan(0)
    }
  })
})

describe('EditorStore canvasSize', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('空节点返回基础尺寸', () => {
    const store = useEditorStore()
    expect(store.canvasSize.width).toBeGreaterThanOrEqual(800)
    expect(store.canvasSize.height).toBeGreaterThanOrEqual(600)
  })

  it('节点超出基础尺寸时扩展画布', () => {
    const store = useEditorStore()
    store.nodes = [
      { id: 'n1', type: 'llm', name: 'LLM', position: { x: 2500, y: 100 }, config: {} },
    ]
    expect(store.canvasSize.width).toBeGreaterThan(2500)
  })
})
