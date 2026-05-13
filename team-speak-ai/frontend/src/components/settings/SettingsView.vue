<!--
  SettingsView — 系统设置主内容区页面
  根据 settingsPage 显示对应设置面板。
-->
<template>
  <div class="settings-view">
    <header class="sv-header">
      <span class="material-symbols-outlined sv-header-icon">{{ pageIcon }}</span>
      <h2 class="sv-title">{{ pageTitle }}</h2>
    </header>

    <div class="sv-body">
      <!-- 系统变量 -->
      <div v-if="settingsPage === 'sys_vars'" class="sv-section">
        <SysVarsPanelFull />
      </div>

      <!-- 系统快捷键 -->
      <div v-else-if="settingsPage === 'shortcuts'" class="sv-section">
        <ShortcutsPanel />
      </div>

      <!-- LLM 预设管理 -->
      <div v-else-if="settingsPage === 'llm_settings'" class="sv-section">
        <LlmPresetsPanel />
      </div>

      <!-- OCR 预设管理 -->
      <div v-else-if="settingsPage === 'ocr_settings'" class="sv-section">
        <OcrPresetsPanel />
      </div>

      <div v-else-if="settingsPage === 'stt_settings'" class="sv-section">
        <SttPresetsPanel />
      </div>

      <div v-else-if="settingsPage === 'tts_settings'" class="sv-section">
        <TtsPresetsPanel />
      </div>

      <!-- TeamSpeak 连接预设 -->
      <div v-else-if="settingsPage === 'ts_settings'" class="sv-section">
        <TeamSpeakPresetsPanel />
      </div>

      <!-- VAD 预设管理 -->
      <div v-else-if="settingsPage === 'vad_settings'" class="sv-section">
        <VadPresetsPanel />
      </div>

      <div v-else class="sv-section sv-placeholder">
        <span class="material-symbols-outlined" style="font-size: 48px; opacity: 0.15;">settings</span>
        <p>选择左侧设置项</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SysVarsPanelFull from './SysVarsPanelFull.vue'
import ShortcutsPanel from './ShortcutsPanel.vue'
import LlmPresetsPanel from './LlmPresetsPanel.vue'
import TtsPresetsPanel from './TtsPresetsPanel.vue'
import SttPresetsPanel from './SttPresetsPanel.vue'
import TeamSpeakPresetsPanel from './TeamSpeakPresetsPanel.vue'
import OcrPresetsPanel from './OcrPresetsPanel.vue'
import VadPresetsPanel from './VadPresetsPanel.vue'

const props = defineProps({
  settingsPage: { type: String, default: '' },
  providerStatus: { type: Object, default: () => ({}) },
})

const pageTitle = computed(() => ({
  sys_vars: '系统变量',
  shortcuts: '系统快捷键',
  ocr_settings: 'OCR 设置',
  llm_settings: 'LLM 设置',
  stt_settings: 'STT 设置',
  tts_settings: 'TTS 设置',
  ts_settings: 'TeamSpeak 连接',
  vad_settings: 'VAD 设置',
}[props.settingsPage] || '系统设置'))

const pageIcon = computed(() => ({
  sys_vars: 'data_object',
  shortcuts: 'keyboard',
  ocr_settings: 'document_scanner',
  llm_settings: 'psychology',
  stt_settings: 'mic',
  tts_settings: 'record_voice_over',
  ts_settings: 'headset_mic',
  vad_settings: 'voice_selection',
}[props.settingsPage] || 'settings'))
</script>

<style scoped>
.settings-view {
  height: 100%;
  display: flex; flex-direction: column;
  background: #10131b; color: #e0e2ed;
  overflow-y: auto;
}

.sv-header {
  display: flex; align-items: center; gap: 12px;
  padding: 24px 32px 16px;
  border-bottom: 1px solid rgba(65, 71, 84, 0.3);
}
.sv-header-icon { font-size: 28px; color: #adc7ff; }
.sv-title { font-size: 20px; font-weight: 600; font-family: 'Space Grotesk', sans-serif; margin: 0; }

.sv-body {
  flex: 1; padding: 24px 32px;
}

.sv-section { margin-bottom: 24px; }

.sv-info-row {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 16px; border-radius: 8px;
  background: rgba(173, 199, 255, 0.04);
  border: 1px solid rgba(65, 71, 84, 0.3);
}
.sv-label { font-size: 13px; color: #8b90a0; min-width: 100px; }
.sv-value { font-size: 14px; font-family: 'Space Grotesk', monospace; color: #adc7ff; }

.sv-placeholder {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 80px 0; color: #64748b;
}
.sv-placeholder p { margin-top: 12px; font-size: 14px; }
</style>
