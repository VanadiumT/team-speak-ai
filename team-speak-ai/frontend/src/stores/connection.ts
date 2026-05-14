/**
 * Connection Store — WebSocket 连接与服务状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline'
import type { ServiceStatus } from '@/types/pipeline'

export const useConnectionStore = defineStore('connection', () => {
  const isConnected = ref(false)
  const services = ref<ServiceStatus[]>([])
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

  function onConnected(): void {
    isConnected.value = true
    reconnectAttempts.value = 0
  }

  function onDisconnected(): void {
    isConnected.value = false
  }

  function onConnectionStatus({ services: svcs }: { services?: ServiceStatus[] }): void {
    if (svcs) {
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
  function init(): void {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('connected', onConnected as (p: Record<string, unknown>) => void)
    pipelineSocket.on('disconnected', onDisconnected as (p: Record<string, unknown>) => void)
    pipelineSocket.on('connection.status', onConnectionStatus as (p: Record<string, unknown>) => void)
  }

  return {
    isConnected, services, reconnectAttempts,
    tsBotStatus, backendStatus, pipelineStatus,
    init,
  }
})
