/**
 * Connection Store — WebSocket 连接与服务状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useConnectionStore = defineStore('connection', () => {
  const isConnected = ref(false)
  const services = ref([])            // ServiceStatus[]
  const reconnectAttempts = ref(0)

  const tsBotStatus = computed(() => {
    const s = services.value.find((s) => s.id === 'ts_bot')
    return s?.status || 'unknown'
  })

  const backendStatus = computed(() => {
    const s = services.value.find((s) => s.id === 'backend')
    return s?.status || 'unknown'
  })

  const pipelineStatus = computed(() => {
    const s = services.value.find((s) => s.id === 'pipeline')
    return s?.status || 'unknown'
  })

  function onConnected() {
    isConnected.value = true
    reconnectAttempts.value = 0
  }

  function onDisconnected() {
    isConnected.value = false
  }

  function onConnectionStatus({ services: svcs }) {
    if (svcs) {
      // 合并更新（后端可能只发变更项）
      for (const svc of svcs) {
        const idx = services.value.findIndex((s) => s.id === svc.id)
        if (idx >= 0) {
          services.value[idx] = { ...services.value[idx], ...svc }
        } else {
          services.value.push(svc)
        }
      }
    }
  }

  let _initialized = false
  function init() {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('connected', onConnected)
    pipelineSocket.on('disconnected', onDisconnected)
    pipelineSocket.on('connection.status', onConnectionStatus)
  }

  return {
    isConnected, services, reconnectAttempts,
    tsBotStatus, backendStatus, pipelineStatus,
    init,
  }
})
