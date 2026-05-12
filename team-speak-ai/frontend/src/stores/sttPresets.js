/**
 * STT Presets Store — STT 平台预设 & 模型配置
 *
 * 管理平台 + 模型的两层预设列表，参照 presets.js (LLM) 结构。
 * 数据由后端 stt_presets.list 事件推送，修改通过 WS 命令。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useSttPresetsStore = defineStore('sttPresets', () => {
  const platforms = ref([])

  // ── 扁平化模型列表 ──
  const allModels = computed(() => {
    const result = []
    for (const p of platforms.value) {
      for (const m of (p.models || [])) {
        result.push({
          platformId: p.id,
          modelId: m.id,
          label: `${p.name} / ${m.name}`,
          provider: p.provider,
          language: m.language || 'auto',
          sampleRate: m.sample_rate || 16000,
          isDefault: !!m.is_default,
        })
      }
    }
    return result
  })

  const defaultModel = computed(() =>
    allModels.value.find(m => m.isDefault) || allModels.value[0]
  )

  function getLabel(platformId, modelId) {
    const m = allModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m ? m.label : '未知模型'
  }

  function getModelInfo(platformId, modelId) {
    const m = allModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m || null
  }

  // ── WS 事件 ──
  function onSttPresetsList(data) {
    if (data && data.platforms) {
      platforms.value = data.platforms
    }
  }

  // ── CRUD ──
  async function savePlatform(platform) {
    await pipelineSocket.sendCommand('_system', 'stt_preset.save_platform', { platform })
  }

  async function deletePlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'stt_preset.delete_platform', { platform_id: platformId })
  }

  async function duplicatePlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'stt_preset.duplicate_platform', { platform_id: platformId })
  }

  async function saveModel(platformId, model) {
    await pipelineSocket.sendCommand('_system', 'stt_preset.save_model', { platform_id: platformId, model })
  }

  async function deleteModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'stt_preset.delete_model', { platform_id: platformId, model_id: modelId })
  }

  async function duplicateModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'stt_preset.duplicate_model', { platform_id: platformId, model_id: modelId })
  }

  let _init = false
  function init() {
    if (_init) return
    _init = true
    pipelineSocket.on('stt_presets.list', onSttPresetsList)
  }

  return {
    platforms, allModels, defaultModel,
    getLabel, getModelInfo,
    savePlatform, deletePlatform, duplicatePlatform,
    saveModel, deleteModel, duplicateModel,
    init,
  }
})
