/**
 * Preheat Store — 模型预热配置管理
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pipelineSocket } from '@/api/pipeline'

export interface ProviderPreheatConfig {
  enabled: boolean
}

export interface PreheatConfig {
  enabled: boolean
  ocr: ProviderPreheatConfig
  stt: ProviderPreheatConfig
}

const defaultConfig: PreheatConfig = {
  enabled: true,
  ocr: { enabled: true },
  stt: { enabled: true },
}

export const usePreheatStore = defineStore('preheat', () => {
  const config = ref<PreheatConfig>({ ...defaultConfig })
  const loading = ref(false)

  function _ensureConnected(): Promise<void> {
    return new Promise((resolve) => {
      if (pipelineSocket.connected) {
        resolve()
        return
      }
      const onConn = () => {
        pipelineSocket.off('connected', onConn)
        resolve()
      }
      pipelineSocket.on('connected', onConn)
    })
  }

  async function fetchConfig(): Promise<void> {
    loading.value = true
    try {
      await _ensureConnected()
      await pipelineSocket.sendCommand('_system', 'preheat.get_config', {})
    } catch (e) {
      console.error('[preheat] Failed to fetch config:', e)
    } finally {
      loading.value = false
    }
  }

  async function updateConfig(patch: Partial<PreheatConfig>): Promise<void> {
    try {
      await _ensureConnected()
      await pipelineSocket.sendCommand('_system', 'preheat.update_config', patch)
    } catch (e) {
      console.error('[preheat] Failed to update config:', e)
    }
  }

  function onConfigResult(data: PreheatConfig): void {
    config.value = { ...defaultConfig, ...data }
  }

  let _initialized = false
  function init(): void {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('preheat.config', onConfigResult)
    fetchConfig()
  }

  return { config, loading, fetchConfig, updateConfig, init }
})
