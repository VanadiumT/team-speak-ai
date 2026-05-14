/**
 * Sidebar Store — 侧栏树状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline'
import { useEditorStore } from './editor'
import type { SidebarNode, FlowSummary } from '@/types/pipeline'

export const useSidebarStore = defineStore('sidebar', () => {
  const sidebarTree = ref<SidebarNode[]>([])
  const expandedSections = ref<Set<string>>(new Set())
  const activeFlowId = ref<string | null>(null)
  const recentFlows = ref<{ id: string; name: string; icon: string }[]>([])

  const availableGroups = computed(() => {
    const paths = new Set<string>()
    function walk(nodes: SidebarNode[], prefix: string = ''): void {
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

  function isExpanded(id: string): boolean { return expandedSections.value.has(id) }

  function toggleSection(id: string): void {
    if (expandedSections.value.has(id)) {
      expandedSections.value.delete(id)
    } else {
      expandedSections.value.add(id)
    }
    expandedSections.value = new Set(expandedSections.value)
  }

  function updateRecent(flowId: string, flowName: string, flowIcon: string): void {
    const stored: { id: string; name: string; icon: string }[] = JSON.parse(localStorage.getItem('recent-flows') || '[]')
    const filtered = stored.filter((r) => r.id !== flowId)
    filtered.unshift({ id: flowId, name: flowName, icon: flowIcon })
    recentFlows.value = filtered.slice(0, 5)
    localStorage.setItem('recent-flows', JSON.stringify(recentFlows.value))
  }

  async function selectFlow(flowId: string): Promise<void> {
    activeFlowId.value = flowId
    const editorStore = useEditorStore()
    editorStore.exitEditMode()
    try {
      await editorStore.loadFlow(flowId)
      const meta = editorStore.flowMeta
      updateRecent(flowId, (meta.name as string) || '', (meta.icon as string) || '')
    } catch (e) {
      console.error('Failed to load flow:', e)
    }
  }

  function init(): void {
    pipelineSocket.on('sidebar.tree', (params: Record<string, unknown>) => {
      const groups = (params.groups as SidebarNode[]) || []
      sidebarTree.value = groups
      const fresh = new Set<string>()
      function expandAll(nodes: SidebarNode[]): void {
        for (const n of nodes) {
          if (n.type === 'section' || n.type === 'group') {
            fresh.add(n.id)
            if (n.children) expandAll(n.children)
          }
        }
      }
      expandAll(groups)
      expandedSections.value = fresh
    })

    let _pendingAutoOpen: string | null = null
    pipelineSocket.on('flow.created', (params: Record<string, unknown>) => {
      const flow = params.flow as FlowSummary | undefined
      if (flow && flow.id) {
        _pendingAutoOpen = flow.id
        setTimeout(() => {
          if (_pendingAutoOpen === flow!.id) {
            selectFlow(flow!.id)
            _pendingAutoOpen = null
          }
        }, 100)
      }
    })

    pipelineSocket.on('flow.deleted', (params: Record<string, unknown>) => {
      const flow_id = params.flow_id as string
      if (activeFlowId.value === flow_id) {
        activeFlowId.value = null
        const editorStore = useEditorStore()
        editorStore.exitEditMode()
      }
    })

    pipelineSocket.on('flow.copied', (params: Record<string, unknown>) => {
      const flow = params.flow as FlowSummary | undefined
      if (flow && flow.id) {
        _pendingAutoOpen = flow.id
        setTimeout(() => {
          if (_pendingAutoOpen === flow!.id) {
            selectFlow(flow!.id)
            _pendingAutoOpen = null
          }
        }, 100)
      }
    })

    pipelineSocket.on('flow.enabled_toggled', (params: Record<string, unknown>) => {
      const flow_id = params.flow_id as string
      const enabled = params.enabled as boolean
      function updateNode(nodes: SidebarNode[]): boolean {
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

    pipelineSocket.on('flow.group_deleted', (params: Record<string, unknown>) => {
      const group_path = params.group_path as string
      const editorStore = useEditorStore()
      const flowGroup = (editorStore.flowMeta.group as string) || ''
      if (flowGroup === group_path || flowGroup.startsWith(group_path + '/')) {
        activeFlowId.value = null
        editorStore.exitEditMode()
        editorStore.nodes = []
        editorStore.connections = []
      }
    })

    recentFlows.value = JSON.parse(localStorage.getItem('recent-flows') || '[]').slice(0, 5)
  }

  return {
    sidebarTree, expandedSections, activeFlowId, recentFlows,
    availableGroups,
    isExpanded, toggleSection, selectFlow, updateRecent,
    init,
  }
})
