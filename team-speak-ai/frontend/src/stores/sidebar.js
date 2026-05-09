/**
 * Sidebar Store — 侧栏树状态
 *
 * 接收后端 sidebar.tree 推送，维护树结构、展开/折叠状态、当前选中流程。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'
import { useEditorStore } from './editor.js'

export const useSidebarStore = defineStore('sidebar', () => {
  // ── 状态 ──
  const sidebarTree = ref([])
  const expandedSections = ref(new Set())
  const activeFlowId = ref(null)
  const recentFlows = ref([])

  // ── 计算属性 ──
  const availableGroups = computed(() => {
    const paths = new Set()
    function walk(nodes, prefix = '') {
      for (const n of nodes) {
        if (n.type === 'group') {
          const path = prefix ? prefix + '/' + n.name : n.name
          paths.add(path)
          if (n.children) walk(n.children, path)
        }
      }
    }
    for (const s of sidebarTree.value) {
      if (s.children) walk(s.children)
    }
    return [...paths].sort()
  })

  // ── 方法 ──
  function isExpanded(id) { return expandedSections.value.has(id) }

  function toggleSection(id) {
    if (expandedSections.value.has(id)) {
      expandedSections.value.delete(id)
    } else {
      expandedSections.value.add(id)
    }
    expandedSections.value = new Set(expandedSections.value)
  }

  function updateRecent(flowId, flowName, flowIcon) {
    const stored = JSON.parse(localStorage.getItem('recent-flows') || '[]')
    const filtered = stored.filter((r) => r.id !== flowId)
    filtered.unshift({ id: flowId, name: flowName, icon: flowIcon })
    recentFlows.value = filtered.slice(0, 5)
    localStorage.setItem('recent-flows', JSON.stringify(recentFlows.value))
  }

  async function selectFlow(flowId) {
    activeFlowId.value = flowId
    const editorStore = useEditorStore()
    editorStore.exitEditMode()
    try {
      await editorStore.loadFlow(flowId)
      const meta = editorStore.flowMeta
      updateRecent(flowId, meta.name || '', meta.icon || '')
    } catch (e) {
      console.error('Failed to load flow:', e)
    }
  }

  // ── 事件注册 ──
  function init() {
    pipelineSocket.on('sidebar.tree', ({ groups }) => {
      sidebarTree.value = groups || []
      const fresh = new Set()
      function expandAll(nodes) {
        for (const n of nodes) {
          if (n.type === 'section' || n.type === 'group') {
            fresh.add(n.id)
            if (n.children) expandAll(n.children)
          }
        }
      }
      expandAll(groups || [])
      expandedSections.value = fresh
    })

    let _pendingAutoOpen = null
    pipelineSocket.on('flow.created', ({ flow }) => {
      if (flow && flow.id) {
        _pendingAutoOpen = flow.id
        setTimeout(() => {
          if (_pendingAutoOpen === flow.id) {
            selectFlow(flow.id)
            _pendingAutoOpen = null
          }
        }, 100)
      }
    })

    pipelineSocket.on('flow.deleted', ({ flow_id }) => {
      if (activeFlowId.value === flow_id) {
        activeFlowId.value = null
        const editorStore = useEditorStore()
        editorStore.exitEditMode()
      }
    })

    pipelineSocket.on('flow.copied', ({ flow }) => {
      if (flow && flow.id) {
        _pendingAutoOpen = flow.id
        setTimeout(() => {
          if (_pendingAutoOpen === flow.id) {
            selectFlow(flow.id)
            _pendingAutoOpen = null
          }
        }, 100)
      }
    })

    pipelineSocket.on('flow.enabled_toggled', ({ flow_id, enabled }) => {
      function updateNode(nodes) {
        for (const n of nodes) {
          if (n.type === 'flow_ref' && n.flow_id === flow_id) {
            n.enabled = enabled
            return true
          }
          if (n.children && updateNode(n.children)) return true
        }
        return false
      }
      updateNode(sidebarTree.value)
      const editorStore = useEditorStore()
      if (editorStore.flowId === flow_id) {
        editorStore.flowMeta.enabled = enabled
      }
    })

    pipelineSocket.on('flow.group_deleted', ({ group_path }) => {
      const editorStore = useEditorStore()
      const flowGroup = editorStore.flowMeta.group || ''
      if (flowGroup === group_path || flowGroup.startsWith(group_path + '/')) {
        activeFlowId.value = null
        editorStore.exitEditMode()
        editorStore.nodes = []
        editorStore.connections = []
      }
    })

    // Load recent flows from localStorage
    recentFlows.value = JSON.parse(localStorage.getItem('recent-flows') || '[]').slice(0, 5)
  }

  return {
    sidebarTree, expandedSections, activeFlowId, recentFlows,
    availableGroups,
    isExpanded, toggleSection, selectFlow, updateRecent,
    init,
  }
})
