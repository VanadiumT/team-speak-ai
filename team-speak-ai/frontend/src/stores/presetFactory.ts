/**
 * Preset Store Factory — 为 LLM/TTS/STT/OCR/VAD/TS 生成统一的 Pinia store
 *
 * 所有预设类型共享相同的 CRUD + computed 模式，只需传入差异化配置。
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { pipelineSocket } from '@/api/pipeline'
import type { PresetPlatform } from '@/types/pipeline'

export interface PresetStoreOptions {
  storeName: string
  eventName: string
  commandPrefix: string
  modelFields: (platform: PresetPlatform, model: Record<string, unknown>) => Record<string, unknown>
  extra?: Record<string, unknown>
}

export interface PresetStoreReturn {
  platforms: Ref<PresetPlatform[]>
  allModels: ComputedRef<Record<string, unknown>[]>
  defaultModel: ComputedRef<Record<string, unknown> | undefined>
  getLabel: (platformId: string, modelId: string) => string
  getModelInfo: (platformId: string, modelId: string) => Record<string, unknown> | null
  savePlatform: (platform: PresetPlatform) => Promise<void>
  deletePlatform: (platformId: string) => Promise<void>
  duplicatePlatform: (platformId: string) => Promise<void>
  saveModel: (platformId: string, model: Record<string, unknown>) => Promise<void>
  deleteModel: (platformId: string, modelId: string) => Promise<void>
  duplicateModel: (platformId: string, modelId: string) => Promise<void>
  init: () => void
  [key: string]: unknown
}

export function createPresetStore(options: PresetStoreOptions): () => PresetStoreReturn {
  const { storeName, eventName, commandPrefix, modelFields, extra = {} } = options

  const setup = (): PresetStoreReturn => {
    const platforms = ref<PresetPlatform[]>([])

    const allModels = computed(() => {
      const result: Record<string, unknown>[] = []
      for (const p of platforms.value) {
        for (const m of (p.models || [])) {
          result.push(modelFields(p, m as unknown as Record<string, unknown>))
        }
      }
      return result
    })

    const defaultModel = computed(() =>
      allModels.value.find(m => m.isDefault) || allModels.value[0]
    )

    function getLabel(platformId: string, modelId: string): string {
      const m = allModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
      return m ? (m.label as string) : '未知模型'
    }

    function getModelInfo(platformId: string, modelId: string): Record<string, unknown> | null {
      return allModels.value.find(x => x.platformId === platformId && x.modelId === modelId) || null
    }

    function onPresetsList(data: Record<string, unknown>): void {
      if (data && data.platforms) {
        platforms.value = data.platforms as PresetPlatform[]
      }
    }

    async function savePlatform(platform: PresetPlatform): Promise<void> {
      await pipelineSocket.sendCommand('_system', `${commandPrefix}.save_platform`, { platform })
    }

    async function deletePlatform(platformId: string): Promise<void> {
      await pipelineSocket.sendCommand('_system', `${commandPrefix}.delete_platform`, { platform_id: platformId })
    }

    async function duplicatePlatform(platformId: string): Promise<void> {
      await pipelineSocket.sendCommand('_system', `${commandPrefix}.duplicate_platform`, { platform_id: platformId })
    }

    async function saveModel(platformId: string, model: Record<string, unknown>): Promise<void> {
      await pipelineSocket.sendCommand('_system', `${commandPrefix}.save_model`, { platform_id: platformId, model })
    }

    async function deleteModel(platformId: string, modelId: string): Promise<void> {
      await pipelineSocket.sendCommand('_system', `${commandPrefix}.delete_model`, { platform_id: platformId, model_id: modelId })
    }

    async function duplicateModel(platformId: string, modelId: string): Promise<void> {
      await pipelineSocket.sendCommand('_system', `${commandPrefix}.duplicate_model`, { platform_id: platformId, model_id: modelId })
    }

    let _init = false
    function init(): void {
      if (_init) return
      _init = true
      pipelineSocket.on(eventName, onPresetsList)
    }

    return {
      platforms, allModels, defaultModel,
      getLabel, getModelInfo,
      savePlatform, deletePlatform, duplicatePlatform,
      saveModel, deleteModel, duplicateModel,
      init,
      ...extra,
    }
  }

  return setup
}
