import { defineStore } from 'pinia'
import { pipelineSocket } from '@/api/pipeline'

/**
 * 侧边栏 Store — 从后端配置动态渲染
 */
export const useSidebarStore = defineStore('sidebar', {
  state: () => ({
    groups: [],
    activeFeatureId: null,
    expandedGroups: new Set(),
    loading: false,
  }),

  actions: {
    loadFromConfig(configs) {
      // configs = backend PipelineDefinition list
      // 按 group 分组
      const groupMap = {}
      configs.forEach((cfg) => {
        const g = cfg.group || 'default'
        if (!groupMap[g]) groupMap[g] = { id: g, name: this._groupName(g), icon: '📋', children: [] }
        groupMap[g].children.push(cfg)
      })
      this.groups = Object.values(groupMap)
      this.groups.forEach((g) => this.expandedGroups.add(g.id))
    },

    _groupName(g) {
      const names = {
        game_features: '游戏功能',
        core_features: '核心功能',
        default: '其他',
      }
      return names[g] || g
    },

    setActive(featureId) {
      this.activeFeatureId = featureId
    },

    toggleGroup(groupId) {
      if (this.expandedGroups.has(groupId)) {
        this.expandedGroups.delete(groupId)
      } else {
        this.expandedGroups.add(groupId)
      }
    },
  },
})
