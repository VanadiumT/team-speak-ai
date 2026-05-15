<!--
  PreheatPanel — 模型预热设置
  控制应用启动时是否预加载 OCR/STT 模型。
-->
<template>
  <div class="ph-panel">
    <p class="ph-desc">预热在后端启动时自动执行，仅加载默认配置的模型。关闭后模型将在首次使用时加载。</p>

    <!-- 全局开关 -->
    <div class="ph-row ph-global">
      <div class="ph-row-info">
        <span class="material-symbols-outlined ph-icon">power_settings_new</span>
        <div>
          <div class="ph-label">全局预热</div>
          <div class="ph-sub">关闭后跳过所有模型预热</div>
        </div>
      </div>
      <label class="ph-toggle">
        <input type="checkbox" :checked="config.enabled" @change="toggleGlobal" />
        <span class="ph-slider"></span>
      </label>
    </div>

    <div class="ph-divider"></div>

    <!-- OCR -->
    <div class="ph-row" :class="{ disabled: !config.enabled }">
      <div class="ph-row-info">
        <span class="material-symbols-outlined ph-icon">document_scanner</span>
        <div>
          <div class="ph-label">OCR 模型</div>
          <div class="ph-sub">EasyOCR / PaddleOCR 文字识别模型预加载</div>
        </div>
      </div>
      <label class="ph-toggle">
        <input
          type="checkbox"
          :checked="config.ocr?.enabled"
          :disabled="!config.enabled"
          @change="toggleProvider('ocr')"
        />
        <span class="ph-slider"></span>
      </label>
    </div>

    <!-- STT -->
    <div class="ph-row" :class="{ disabled: !config.enabled }">
      <div class="ph-row-info">
        <span class="material-symbols-outlined ph-icon">mic</span>
        <div>
          <div class="ph-label">STT 模型</div>
          <div class="ph-sub">SenseVoice / Whisper 语音识别模型预加载</div>
        </div>
      </div>
      <label class="ph-toggle">
        <input
          type="checkbox"
          :checked="config.stt?.enabled"
          :disabled="!config.enabled"
          @change="toggleProvider('stt')"
        />
        <span class="ph-slider"></span>
      </label>
    </div>

    <div class="ph-note">
      <span class="material-symbols-outlined" style="font-size: 16px;">info</span>
      TTS、LLM、VAD 为轻量级 API 调用，无需预热。
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { usePreheatStore } from '@/stores/preheat'

const store = usePreheatStore()
const { config } = storeToRefs(store)

function toggleGlobal() {
  store.updateConfig({ enabled: !config.value.enabled })
}

function toggleProvider(key) {
  store.updateConfig({ [key]: { enabled: !config.value[key]?.enabled } })
}

onMounted(() => store.init())
</script>

<style scoped>
.ph-panel {
  display: flex; flex-direction: column; gap: 0;
}
.ph-desc {
  font-size: 13px; color: #8b90a0; margin: 0 0 20px;
  line-height: 1.5;
}

.ph-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-radius: 10px;
  background: rgba(173, 199, 255, 0.03);
  border: 1px solid rgba(65, 71, 84, 0.25);
  margin-bottom: 10px;
  transition: opacity 0.2s;
}
.ph-row.disabled { opacity: 0.45; }
.ph-global { background: rgba(173, 199, 255, 0.06); }

.ph-row-info { display: flex; align-items: center; gap: 14px; }
.ph-icon { font-size: 22px; color: #adc7ff; }
.ph-label { font-size: 14px; font-weight: 500; color: #e0e2ed; }
.ph-sub { font-size: 12px; color: #64748b; margin-top: 2px; }

.ph-divider {
  height: 1px; background: rgba(65, 71, 84, 0.2);
  margin: 16px 0;
}

/* Toggle switch */
.ph-toggle {
  position: relative; display: inline-block;
  width: 44px; height: 24px; flex-shrink: 0;
}
.ph-toggle input { opacity: 0; width: 0; height: 0; }
.ph-slider {
  position: absolute; cursor: pointer; inset: 0;
  background: #2a2e3d; border-radius: 12px;
  transition: background 0.2s;
}
.ph-slider::before {
  content: ''; position: absolute;
  height: 18px; width: 18px; left: 3px; bottom: 3px;
  background: #64748b; border-radius: 50%;
  transition: transform 0.2s, background 0.2s;
}
.ph-toggle input:checked + .ph-slider { background: rgba(78, 222, 163, 0.3); }
.ph-toggle input:checked + .ph-slider::before {
  transform: translateX(20px); background: #4edea3;
}

.ph-note {
  display: flex; align-items: center; gap: 8px;
  margin-top: 16px; padding: 12px 16px;
  border-radius: 8px; font-size: 12px; color: #64748b;
  background: rgba(173, 199, 255, 0.02);
  border: 1px solid rgba(65, 71, 84, 0.15);
}
</style>
