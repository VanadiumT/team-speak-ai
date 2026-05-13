/**
 * Presets Store — LLM 平台预设 & 模型配置
 *
 * 管理平台 + 模型的两层预设列表。
 * 数据由后端 presets.list 事件推送，修改通过 WS 命令。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const usePresetsStore = defineStore('presets', () => {
  const platforms = ref([])

  // ── 扁平化模型列表：用于节点模型下拉 ──
  const allModels = computed(() => {
    const result = []
    for (const p of platforms.value) {
      for (const m of (p.models || [])) {
        result.push({
          platformId: p.id,
          modelId: m.id,
          label: `${p.name} / ${m.name}`,
          provider: p.provider,
          vision: m.vision || false,
          streaming: m.streaming !== false,
          thinkingMode: m.thinking_mode || 'off',
          temperature: m.temperature,
          maxTokens: m.max_tokens,
          isDefault: !!m.is_default,
        })
      }
    }
    return result
  })

  // ── 第一个默认模型 ──
  const defaultModel = computed(() => allModels.value.find(m => m.isDefault) || allModels.value[0])

  function getLabel(platformId, modelId) {
    const m = allModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m ? m.label : '未知模型'
  }

  function getModelInfo(platformId, modelId) {
    const m = allModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m || null
  }

  // ── WS 事件处理 ──
  function onPresetsList(data) {
    if (data && data.platforms) {
      platforms.value = data.platforms
    }
  }

  // ── CRUD actions ──
  async function savePlatform(platform) {
    await pipelineSocket.sendCommand('_system', 'preset.save_platform', { platform })
  }

  async function deletePlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'preset.delete_platform', { platform_id: platformId })
  }

  async function duplicatePlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'preset.duplicate_platform', { platform_id: platformId })
  }

  async function saveModel(platformId, model) {
    await pipelineSocket.sendCommand('_system', 'preset.save_model', { platform_id: platformId, model })
  }

  async function deleteModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'preset.delete_model', { platform_id: platformId, model_id: modelId })
  }

  async function duplicateModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'preset.duplicate_model', { platform_id: platformId, model_id: modelId })
  }

  let _init = false
  function init() {
    if (_init) return
    _init = true
    pipelineSocket.on('presets.list', onPresetsList)
  }

  // ═══════════════════════════════════════════════════
  // TTS 预设
  // ═══════════════════════════════════════════════════

  const ttsPlatforms = ref([])

  const ttsAllModels = computed(() => {
    const result = []
    for (const p of ttsPlatforms.value) {
      for (const m of (p.models || [])) {
        result.push({
          platformId: p.id,
          modelId: m.id,
          label: `${p.name} / ${m.name}`,
          provider: p.provider,
          voiceId: m.voice_id || '',
          streaming: m.streaming !== false,
          speed: m.speed,
          isDefault: !!m.is_default,
        })
      }
    }
    return result
  })

  const ttsDefaultModel = computed(() => ttsAllModels.value.find(m => m.isDefault) || ttsAllModels.value[0])

  function getTtsLabel(platformId, modelId) {
    const m = ttsAllModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m ? m.label : '未知模型'
  }

  function onTtsPresetsList(data) {
    if (data && data.platforms) {
      ttsPlatforms.value = data.platforms
    }
  }

  async function saveTtsPlatform(platform) {
    await pipelineSocket.sendCommand('_system', 'tts_preset.save_platform', { platform })
  }

  async function deleteTtsPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'tts_preset.delete_platform', { platform_id: platformId })
  }

  async function duplicateTtsPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'tts_preset.duplicate_platform', { platform_id: platformId })
  }

  async function saveTtsModel(platformId, model) {
    await pipelineSocket.sendCommand('_system', 'tts_preset.save_model', { platform_id: platformId, model })
  }

  async function deleteTtsModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'tts_preset.delete_model', { platform_id: platformId, model_id: modelId })
  }

  async function duplicateTtsModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'tts_preset.duplicate_model', { platform_id: platformId, model_id: modelId })
  }

  let _ttsInit = false
  function initTts() {
    if (_ttsInit) return
    _ttsInit = true
    pipelineSocket.on('tts_presets.list', onTtsPresetsList)
  }

  // ═══════════════════════════════════════════════════
  // OCR 预设
  // ═══════════════════════════════════════════════════

  const ocrPlatforms = ref([])

  const ocrAllModels = computed(() => {
    const result = []
    for (const p of ocrPlatforms.value) {
      for (const m of (p.models || [])) {
        result.push({
          platformId: p.id,
          modelId: m.id,
          label: `${p.name} / ${m.name}`,
          provider: p.provider,
          langList: m.lang_list || [],
          lang: m.lang || '',
          gpu: !!m.gpu,
          useAngleCls: m.use_angle_cls !== false,
          confidenceThreshold: m.confidence_threshold ?? 0.3,
          isDefault: !!m.is_default,
        })
      }
    }
    return result
  })

  const ocrDefaultModel = computed(() => ocrAllModels.value.find(m => m.isDefault) || ocrAllModels.value[0])

  function getOcrLabel(platformId, modelId) {
    const m = ocrAllModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m ? m.label : '未知预设'
  }

  function getOcrModelInfo(platformId, modelId) {
    const m = ocrAllModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m || null
  }

  function onOcrPresetsList(data) {
    if (data && data.platforms) {
      ocrPlatforms.value = data.platforms
    }
  }

  async function saveOcrPlatform(platform) {
    await pipelineSocket.sendCommand('_system', 'ocr_preset.save_platform', { platform })
  }

  async function deleteOcrPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'ocr_preset.delete_platform', { platform_id: platformId })
  }

  async function duplicateOcrPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'ocr_preset.duplicate_platform', { platform_id: platformId })
  }

  async function saveOcrModel(platformId, model) {
    await pipelineSocket.sendCommand('_system', 'ocr_preset.save_model', { platform_id: platformId, model })
  }

  async function deleteOcrModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'ocr_preset.delete_model', { platform_id: platformId, model_id: modelId })
  }

  async function duplicateOcrModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'ocr_preset.duplicate_model', { platform_id: platformId, model_id: modelId })
  }

  let _ocrInit = false
  function initOcr() {
    if (_ocrInit) return
    _ocrInit = true
    pipelineSocket.on('ocr_presets.list', onOcrPresetsList)
  }

  // ═══════════════════════════════════════════════════
  // VAD 预设
  // ═══════════════════════════════════════════════════

  const vadPlatforms = ref([])

  const vadAllModels = computed(() => {
    const result = []
    for (const p of vadPlatforms.value) {
      for (const m of (p.models || [])) {
        result.push({
          platformId: p.id,
          modelId: m.id,
          label: `${p.name} / ${m.name}`,
          provider: p.provider,
          vadMode: m.vad_mode ?? 3,
          frameDurationMs: m.frame_duration_ms ?? 20,
          hangoverMs: m.hangover_ms ?? 600,
          sampleRate: m.sample_rate ?? 16000,
          minSpeechMs: m.min_speech_ms ?? 300,
          isDefault: !!m.is_default,
        })
      }
    }
    return result
  })

  const vadDefaultModel = computed(() => vadAllModels.value.find(m => m.isDefault) || vadAllModels.value[0])

  function getVadLabel(platformId, modelId) {
    const m = vadAllModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m ? m.label : '未知模型'
  }

  function onVadPresetsList(data) {
    if (data && data.platforms) {
      vadPlatforms.value = data.platforms
    }
  }

  async function saveVadPlatform(platform) {
    await pipelineSocket.sendCommand('_system', 'vad_preset.save_platform', { platform })
  }

  async function deleteVadPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'vad_preset.delete_platform', { platform_id: platformId })
  }

  async function duplicateVadPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'vad_preset.duplicate_platform', { platform_id: platformId })
  }

  async function saveVadModel(platformId, model) {
    await pipelineSocket.sendCommand('_system', 'vad_preset.save_model', { platform_id: platformId, model })
  }

  async function deleteVadModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'vad_preset.delete_model', { platform_id: platformId, model_id: modelId })
  }

  async function duplicateVadModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'vad_preset.duplicate_model', { platform_id: platformId, model_id: modelId })
  }

  let _vadInit = false
  function initVad() {
    if (_vadInit) return
    _vadInit = true
    pipelineSocket.on('vad_presets.list', onVadPresetsList)
  }

  // ═══════════════════════════════════════════════════
  // TeamSpeak Bridge 连接预设
  //
  // Platform = Java Bridge 实例 (ws_url + api_key)
  // Model    = 连接配置 (nickname, auto_reconnect)
  //
  // 注意: TeamSpeak 服务器参数由 Java 项目管理，
  //       这里的配置只关乎 Python←WS→Java Bridge。
  // ═══════════════════════════════════════════════════

  const tsPlatforms = ref([])

  const tsAllModels = computed(() => {
    const result = []
    for (const p of tsPlatforms.value) {
      for (const m of (p.models || [])) {
        result.push({
          platformId: p.id,
          modelId: m.id,
          label: `${p.name} / ${m.name}`,
          wsUrl: p.ws_url || '',
          apiKey: p.api_key || '',
          nickname: m.nickname || 'TeamSpeakAI',
          autoReconnect: m.auto_reconnect !== false,
          reconnectDelay: m.reconnect_delay ?? 3.0,
          loopback: !!m.loopback,
          isDefault: !!m.is_default,
        })
      }
    }
    return result
  })

  const tsDefaultModel = computed(() => tsAllModels.value.find(m => m.isDefault) || tsAllModels.value[0])

  function getTsLabel(platformId, modelId) {
    const m = tsAllModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    return m ? m.label : '未知桥接'
  }

  function getTsEffectiveConfig(platformId, modelId) {
    const m = tsAllModels.value.find(x => x.platformId === platformId && x.modelId === modelId)
    if (!m) return null
    return {
      ws_url: m.wsUrl,
      api_key: m.apiKey,
      nickname: m.nickname,
      auto_reconnect: m.autoReconnect,
      reconnect_delay: m.reconnectDelay,
      loopback: m.loopback,
    }
  }

  function onTsPresetsList(data) {
    if (data && data.platforms) {
      tsPlatforms.value = data.platforms
    }
  }

  async function saveTsPlatform(platform) {
    await pipelineSocket.sendCommand('_system', 'ts_preset.save_platform', { platform })
  }

  async function deleteTsPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'ts_preset.delete_platform', { platform_id: platformId })
  }

  async function duplicateTsPlatform(platformId) {
    await pipelineSocket.sendCommand('_system', 'ts_preset.duplicate_platform', { platform_id: platformId })
  }

  async function saveTsModel(platformId, model) {
    await pipelineSocket.sendCommand('_system', 'ts_preset.save_model', { platform_id: platformId, model })
  }

  async function deleteTsModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'ts_preset.delete_model', { platform_id: platformId, model_id: modelId })
  }

  async function duplicateTsModel(platformId, modelId) {
    await pipelineSocket.sendCommand('_system', 'ts_preset.duplicate_model', { platform_id: platformId, model_id: modelId })
  }

  let _tsInit = false
  function initTs() {
    if (_tsInit) return
    _tsInit = true
    pipelineSocket.on('ts_presets.list', onTsPresetsList)
  }

  return {
    platforms, allModels, defaultModel,
    getLabel, getModelInfo,
    onPresetsList,
    savePlatform, deletePlatform, duplicatePlatform,
    saveModel, deleteModel, duplicateModel,
    init,
    // TTS
    ttsPlatforms, ttsAllModels, ttsDefaultModel,
    getTtsLabel,
    onTtsPresetsList, initTts,
    saveTtsPlatform, deleteTtsPlatform, duplicateTtsPlatform,
    saveTtsModel, deleteTtsModel, duplicateTtsModel,
    // TeamSpeak
    tsPlatforms, tsAllModels, tsDefaultModel,
    getTsLabel, getTsEffectiveConfig,
    onTsPresetsList, initTs,
    saveTsPlatform, deleteTsPlatform, duplicateTsPlatform,
    saveTsModel, deleteTsModel, duplicateTsModel,
    // OCR
    ocrPlatforms, ocrAllModels, ocrDefaultModel,
    getOcrLabel, getOcrModelInfo,
    onOcrPresetsList, initOcr,
    saveOcrPlatform, deleteOcrPlatform, duplicateOcrPlatform,
    saveOcrModel, deleteOcrModel, duplicateOcrModel,
    // VAD
    vadPlatforms, vadAllModels, vadDefaultModel,
    getVadLabel,
    onVadPresetsList, initVad,
    saveVadPlatform, deleteVadPlatform, duplicateVadPlatform,
    saveVadModel, deleteVadModel, duplicateVadModel,
  }
})
