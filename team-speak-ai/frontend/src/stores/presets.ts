/**
 * Presets Store — LLM / TTS / STT / OCR / VAD / TeamSpeak Bridge 统一入口
 */

import { defineStore } from 'pinia'
import { createPresetStore } from './presetFactory'
import type { PresetPlatform } from '@/types/pipeline'

const llm = createPresetStore({
  storeName: '_llm',
  eventName: 'presets.list',
  commandPrefix: 'preset',
  modelFields: (p, m) => ({
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
  }),
})

const tts = createPresetStore({
  storeName: '_tts',
  eventName: 'tts_presets.list',
  commandPrefix: 'tts_preset',
  modelFields: (p, m) => ({
    platformId: p.id,
    modelId: m.id,
    label: `${p.name} / ${m.name}`,
    provider: p.provider,
    voiceId: m.voice_id || '',
    streaming: m.streaming !== false,
    speed: m.speed,
    isDefault: !!m.is_default,
  }),
})

const ocr = createPresetStore({
  storeName: '_ocr',
  eventName: 'ocr_presets.list',
  commandPrefix: 'ocr_preset',
  modelFields: (p, m) => ({
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
  }),
})

const vad = createPresetStore({
  storeName: '_vad',
  eventName: 'vad_presets.list',
  commandPrefix: 'vad_preset',
  modelFields: (p, m) => ({
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
  }),
})

const stt = createPresetStore({
  storeName: '_stt',
  eventName: 'stt_presets.list',
  commandPrefix: 'stt_preset',
  modelFields: (p, m) => ({
    platformId: p.id,
    modelId: m.id,
    label: `${p.name} / ${m.name}`,
    provider: p.provider,
    language: m.language || 'auto',
    sampleRate: m.sample_rate || 16000,
    isDefault: !!m.is_default,
  }),
})

const ts = createPresetStore({
  storeName: '_ts',
  eventName: 'ts_presets.list',
  commandPrefix: 'ts_preset',
  modelFields: (p, m) => ({
    platformId: p.id,
    modelId: m.id,
    label: `${p.name} / ${m.name}`,
    wsUrl: (p as unknown as Record<string, unknown>).ws_url || '',
    apiKey: p.api_key || '',
    nickname: m.nickname || 'TeamSpeakAI',
    autoReconnect: m.auto_reconnect !== false,
    reconnectDelay: m.reconnect_delay ?? 3.0,
    loopback: !!m.loopback,
    isDefault: !!m.is_default,
  }),
  extra: {},
})

export const usePresetsStore = defineStore('presets', () => {
  const llmState = llm()
  const ttsState = tts()
  const ocrState = ocr()
  const vadState = vad()
  const sttState = stt()
  const tsState = ts()

  return {
    // LLM
    platforms: llmState.platforms,
    allModels: llmState.allModels,
    defaultModel: llmState.defaultModel,
    getLabel: llmState.getLabel,
    getModelInfo: llmState.getModelInfo,
    onPresetsList: llmState.onPresetsList,
    init: llmState.init,
    savePlatform: llmState.savePlatform,
    deletePlatform: llmState.deletePlatform,
    duplicatePlatform: llmState.duplicatePlatform,
    saveModel: llmState.saveModel,
    deleteModel: llmState.deleteModel,
    duplicateModel: llmState.duplicateModel,

    // TTS
    ttsPlatforms: ttsState.platforms,
    ttsAllModels: ttsState.allModels,
    ttsDefaultModel: ttsState.defaultModel,
    getTtsLabel: ttsState.getLabel,
    onTtsPresetsList: ttsState.onPresetsList,
    initTts: ttsState.init,
    saveTtsPlatform: ttsState.savePlatform,
    deleteTtsPlatform: ttsState.deletePlatform,
    duplicateTtsPlatform: ttsState.duplicatePlatform,
    saveTtsModel: ttsState.saveModel,
    deleteTtsModel: ttsState.deleteModel,
    duplicateTtsModel: ttsState.duplicateModel,

    // OCR
    ocrPlatforms: ocrState.platforms,
    ocrAllModels: ocrState.allModels,
    ocrDefaultModel: ocrState.defaultModel,
    getOcrLabel: ocrState.getLabel,
    getOcrModelInfo: ocrState.getModelInfo,
    onOcrPresetsList: ocrState.onPresetsList,
    initOcr: ocrState.init,
    saveOcrPlatform: ocrState.savePlatform,
    deleteOcrPlatform: ocrState.deletePlatform,
    duplicateOcrPlatform: ocrState.duplicatePlatform,
    saveOcrModel: ocrState.saveModel,
    deleteOcrModel: ocrState.deleteModel,
    duplicateOcrModel: ocrState.duplicateModel,

    // VAD
    vadPlatforms: vadState.platforms,
    vadAllModels: vadState.allModels,
    vadDefaultModel: vadState.defaultModel,
    getVadLabel: vadState.getLabel,
    onVadPresetsList: vadState.onPresetsList,
    initVad: vadState.init,
    saveVadPlatform: vadState.savePlatform,
    deleteVadPlatform: vadState.deletePlatform,
    duplicateVadPlatform: vadState.duplicatePlatform,
    saveVadModel: vadState.saveModel,
    deleteVadModel: vadState.deleteModel,
    duplicateVadModel: vadState.duplicateModel,

    // STT
    sttPlatforms: sttState.platforms,
    sttAllModels: sttState.allModels,
    sttDefaultModel: sttState.defaultModel,
    getSttLabel: sttState.getLabel,
    getSttModelInfo: sttState.getModelInfo,
    onSttPresetsList: sttState.onPresetsList,
    initStt: sttState.init,
    saveSttPlatform: sttState.savePlatform,
    deleteSttPlatform: sttState.deletePlatform,
    duplicateSttPlatform: sttState.duplicatePlatform,
    saveSttModel: sttState.saveModel,
    deleteSttModel: sttState.deleteModel,
    duplicateSttModel: sttState.duplicateModel,

    // TeamSpeak
    tsPlatforms: tsState.platforms,
    tsAllModels: tsState.allModels,
    tsDefaultModel: tsState.defaultModel,
    getTsLabel: tsState.getLabel,
    getTsEffectiveConfig(platformId: string, modelId: string): Record<string, unknown> | null {
      const m = tsState.allModels.value.find((x: Record<string, unknown>) => x.platformId === platformId && x.modelId === modelId)
      if (!m) return null
      return {
        ws_url: m.wsUrl,
        api_key: m.apiKey,
        nickname: m.nickname,
        auto_reconnect: m.autoReconnect,
        reconnect_delay: m.reconnectDelay,
        loopback: m.loopback,
      }
    },
    onTsPresetsList: tsState.onPresetsList,
    initTs: tsState.init,
    saveTsPlatform: tsState.savePlatform,
    deleteTsPlatform: tsState.deletePlatform,
    duplicateTsPlatform: tsState.duplicatePlatform,
    saveTsModel: tsState.saveModel,
    deleteTsModel: tsState.deleteModel,
    duplicateTsModel: tsState.duplicateModel,
  }
})
