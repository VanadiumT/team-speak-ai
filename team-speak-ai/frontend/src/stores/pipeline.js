import { defineStore } from 'pinia'
import { pipelineSocket } from '@/api/pipeline'

/**
 * Pipeline 状态管理 Store
 *
 * 管理所有功能页的节点运行时状态。
 * 通过 PipelineSocket 接收后端推送，实时更新。
 */
export const usePipelineStore = defineStore('pipeline', {
  state: () => ({
    // featureId → FeatureState
    features: {},

    // 当前选中的
    activeFeatureId: null,
    activeNodeId: null,

    // 重要事件列表
    importantEvents: [],
  }),

  getters: {
    activeFeature: (state) => state.features[state.activeFeatureId] || null,
    activeNode: (state) => {
      const f = state.features[state.activeFeatureId]
      if (!f || !state.activeNodeId) return null
      return f.nodes.find((n) => n.id === state.activeNodeId) || null
    },
    isRunning: (state) => {
      const f = state.features[state.activeFeatureId]
      return f?.status === 'running'
    },
  },

  actions: {
    /** 注册功能页配置 */
    registerFeature(config) {
      this.features[config.id] = {
        config,
        executionId: null,
        status: 'idle',
        nodes: config.nodes.map((n) => ({
          id: n.id,
          type: n.type,
          name: n.name,
          status: 'pending',
          summary: '',
          progress: null,
          data: null,
          error: null,
          listener: n.listener || false,
          trigger: n.trigger || null,
          input_mappings: n.input_mappings || [],
        })),
      }
    },

    /** 订阅功能页 */
    subscribe(featureId) {
      this.activeFeatureId = featureId
      pipelineSocket.send('subscribe', { feature_id: featureId })
    },

    /** 取消订阅 */
    unsubscribe(featureId) {
      pipelineSocket.send('unsubscribe', { feature_id: featureId })
    },

    /** 请求后端配置 */
    fetchConfig() {
      pipelineSocket.send('get_config')
    },

    /** 发送节点操作 */
    nodeAction(nodeId, action, payload = {}) {
      pipelineSocket.send('node_action', {
        feature_id: this.activeFeatureId,
        node_id: nodeId,
        action,
        payload,
      })
    },

    /** 上传文件到指定节点 */
    uploadFile(nodeId, file) {
      const reader = new FileReader()
      reader.onload = () => {
        this.nodeAction(nodeId, 'upload', {
          file: {
            data: reader.result.split(',')[1], // base64
            filename: file.name,
            mime_type: file.type,
          },
        })
      }
      reader.readAsDataURL(file)
    },

    /** 输入文本 */
    inputText(nodeId, text) {
      this.nodeAction(nodeId, 'input_text', { text })
    },

    /** 触发节点 */
    triggerNode(nodeId) {
      this.nodeAction(nodeId, 'trigger')
    },

    /** 重新开始（清除上下文） */
    restart() {
      this.nodeAction('', 'restart')
    },

    /** ===== 事件处理 ===== */

    handleNodeUpdate(data) {
      const { feature_id, node_id, status, summary, progress, data: nodeData } = data
      const feat = this.features[feature_id]
      if (!feat) return
      const node = feat.nodes.find((n) => n.id === node_id)
      if (!node) return
      node.status = status
      if (summary !== undefined) node.summary = summary
      if (progress !== undefined) node.progress = progress
      if (nodeData) node.data = nodeData
    },

    handleNodeComplete(data) {
      const { feature_id, node_id, output } = data
      const feat = this.features[feature_id]
      if (!feat) return
      const node = feat.nodes.find((n) => n.id === node_id)
      if (!node) return
      node.status = 'completed'
      node.progress = 1
      if (output) node.data = output
    },

    handleNodeError(data) {
      const { feature_id, node_id, error } = data
      const feat = this.features[feature_id]
      if (!feat) return
      const node = feat.nodes.find((n) => n.id === node_id)
      if (!node) return
      node.status = 'error'
      node.error = error
    },

    handlePipelineStart(data) {
      const feat = Object.values(this.features).find(
        (f) => f.config.id === data.feature_id
      )
      if (!feat) return
      feat.executionId = data.execution_id
      feat.status = 'running'
      // 重置节点状态
      feat.nodes.forEach((n) => {
        if (!n.listener) {
          n.status = 'pending'
          n.summary = ''
          n.progress = null
          n.data = null
          n.error = null
        }
      })
    },

    handlePipelineComplete(data) {
      const feat = Object.values(this.features).find(
        (f) => f.executionId === data.execution_id
      )
      if (!feat) return
      feat.status = 'completed'
    },

    handlePipelineState(data) {
      // 重连后恢复状态
      const feat = this.features[data.feature_id]
      if (!feat) return
      feat.executionId = data.execution_id
      feat.status = data.status
      if (data.nodes) {
        data.nodes.forEach((n) => {
          const node = feat.nodes.find((x) => x.node_id === n.node_id)
          if (node) {
            node.status = n.status
            node.summary = n.summary || ''
            node.progress = n.progress
            node.error = n.error
            node.data = n.data
          }
        })
      }
    },

    handleImportantUpdate(data) {
      this.importantEvents.unshift({
        id: Date.now(),
        type: data.type || 'info',
        title: data.title || '',
        content: data.content || '',
        timestamp: Date.now(),
      })
      if (this.importantEvents.length > 50) this.importantEvents.pop()
    },
  },
})
