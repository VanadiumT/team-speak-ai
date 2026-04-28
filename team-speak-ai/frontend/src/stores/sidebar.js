/**
 * Sidebar Store — 直接从 sidebar.tree 事件数据渲染侧栏
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useSidebarStore = defineStore('sidebar', () => {
  const tree = ref([])             // SidebarNode[] from sidebar.tree event
  const activeFeatureId = ref(null)
  const expandedGroups = ref(new Set())
  const recentFlows = ref(loadRecentFlows())

  function setActive(id) { activeFeatureId.value = id }

  function toggleGroup(id) {
    if (expandedGroups.value.has(id)) {
      expandedGroups.value.delete(id)
    } else {
      expandedGroups.value.add(id)
    }
    expandedGroups.value = new Set(expandedGroups.value)
  }

  function addRecentFlow(flowId, name) {
    const existing = recentFlows.value.find((f) => f.id === flowId)
    if (existing) recentFlows.value = recentFlows.value.filter((f) => f.id !== flowId)
    recentFlows.value.unshift({ id: flowId, name })
    if (recentFlows.value.length > 5) recentFlows.value = recentFlows.value.slice(0, 5)
    saveRecentFlows(recentFlows.value)
  }

  function init() {
    pipelineSocket.on('sidebar.tree', ({ groups }) => {
      tree.value = groups || []
      groups?.forEach((s) => {
        expandedGroups.value.add(s.id)
        s.children?.forEach((c) => {
          if (c.type === 'group') expandedGroups.value.add(c.id)
        })
      })
    })
  }

  return { tree, activeFeatureId, expandedGroups, recentFlows, setActive, toggleGroup, addRecentFlow, init }
})

function loadRecentFlows() {
  try { return JSON.parse(localStorage.getItem('recentFlows') || '[]') } catch { return [] }
}

function saveRecentFlows(flows) {
  localStorage.setItem('recentFlows', JSON.stringify(flows))
}
