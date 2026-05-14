/**
 * Sidebar Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    sendCommand: vi.fn().mockResolvedValue({}),
    connected: false,
  },
}))

vi.mock('../editor', () => ({
  useEditorStore: vi.fn(() => ({
    exitEditMode: vi.fn(),
    loadFlow: vi.fn().mockResolvedValue({}),
    flowMeta: { name: 'test', icon: 'icon' },
    flowId: null,
    nodes: [],
    connections: [],
  })),
}))

import { useSidebarStore } from '../sidebar'

describe('SidebarStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('初始状态', () => {
    const store = useSidebarStore()
    expect(store.sidebarTree).toEqual([])
    expect(store.activeFlowId).toBeNull()
    expect(store.expandedSections.size).toBe(0)
    expect(store.recentFlows).toEqual([])
  })

  it('toggleSection 展开/折叠', () => {
    const store = useSidebarStore()
    store.toggleSection('section_1')
    expect(store.isExpanded('section_1')).toBe(true)
    store.toggleSection('section_1')
    expect(store.isExpanded('section_1')).toBe(false)
  })

  it('isExpanded 未展开返回 false', () => {
    const store = useSidebarStore()
    expect(store.isExpanded('nonexist')).toBe(false)
  })

  it('updateRecent 保存最近访问', () => {
    const store = useSidebarStore()
    store.updateRecent('flow_1', '流程A', 'icon_a')
    expect(store.recentFlows).toHaveLength(1)
    expect(store.recentFlows[0].id).toBe('flow_1')
    expect(store.recentFlows[0].name).toBe('流程A')
  })

  it('updateRecent 去重并置顶', () => {
    const store = useSidebarStore()
    store.updateRecent('f1', 'A', 'i1')
    store.updateRecent('f2', 'B', 'i2')
    store.updateRecent('f1', 'A', 'i1')
    expect(store.recentFlows).toHaveLength(2)
    expect(store.recentFlows[0].id).toBe('f1')
    expect(store.recentFlows[1].id).toBe('f2')
  })

  it('updateRecent 最多 5 条', () => {
    const store = useSidebarStore()
    for (let i = 0; i < 8; i++) {
      store.updateRecent(`f${i}`, `F${i}`, 'icon')
    }
    expect(store.recentFlows).toHaveLength(5)
  })

  it('availableGroups 从树中提取分组路径', () => {
    const store = useSidebarStore()
    store.sidebarTree = [
      {
        id: 'workflows', name: '工作流', icon: 'account_tree', type: 'section',
        children: [
          {
            id: 'g1', name: '暗区', icon: 'folder', type: 'group',
            children: [
              { id: 'g2', name: '子分组', icon: 'folder', type: 'group', children: [] },
            ],
          },
          { id: 'g3', name: '其他', icon: 'folder', type: 'group', children: [] },
        ],
      },
    ]
    const groups = store.availableGroups
    expect(groups).toContain('暗区')
    expect(groups).toContain('暗区/子分组')
    expect(groups).toContain('其他')
  })

  it('availableGroups 空树返回空数组', () => {
    const store = useSidebarStore()
    expect(store.availableGroups).toEqual([])
  })

  it('sidebarTree 可以被修改', () => {
    const store = useSidebarStore()
    store.sidebarTree = [
      { id: 's1', name: 'Section', icon: 'folder', type: 'section', children: [] },
    ]
    expect(store.sidebarTree).toHaveLength(1)
  })
})
