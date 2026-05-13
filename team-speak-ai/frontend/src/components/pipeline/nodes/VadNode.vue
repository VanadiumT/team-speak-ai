<template>
  <div class="vad-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="model-tag">{{ displayPresetName }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待音频...</div>

      <div v-if="status === 'processing'" class="proc-info">
        <span class="material-symbols-outlined proc-icon">voice_selection</span>
        <span>{{ summary || '分句中...' }}</span>
      </div>

      <div v-if="status === 'completed'" class="done-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>{{ data?.total_chunks ?? 0 }} 句</span>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || 'VAD 分句失败' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="vad-config">
        <div class="cfg-field">
          <label class="cfg-label">VAD 预设</label>
          <select class="cfg-select" :value="selectedModelKey" @change="onModelChange">
            <option v-if="!selectedModelKey" value="" disabled>选择预设...</option>
            <option v-for="m in presetsStore.vadAllModels"
                    :key="m.platformId + '/' + m.modelId"
                    :value="m.platformId + '/' + m.modelId">
              {{ m.label }}
            </option>
          </select>
        </div>

        <details class="cfg-overrides">
          <summary class="cfg-summary">覆盖参数 (可选)</summary>
          <div class="cfg-field">
            <label class="cfg-label">VAD 模式 <span class="cfg-hint">(预设: {{ currentModelInfo?.vadMode ?? 3 }})</span></label>
            <select class="cfg-select" :value="overrideVal('vad_mode')" @change="onOverride('vad_mode', $event.target.value)">
              <option value="">预设</option>
              <option :value="0">0 — 宽松</option>
              <option :value="1">1 — 中等</option>
              <option :value="2">2 — 激进</option>
              <option :value="3">3 — 最激进</option>
            </select>
          </div>
          <div class="cfg-field">
            <label class="cfg-label">Hangover 静音超时 (ms) <span class="cfg-hint">(预设: {{ currentModelInfo?.hangoverMs ?? 600 }})</span></label>
            <input class="cfg-input" type="number" :value="overrideVal('hangover_ms')" @change="onOverride('hangover_ms', $event.target.value)"
                   min="100" max="3000" step="50" :placeholder="String(currentModelInfo?.hangoverMs ?? 600)" />
          </div>
          <div class="cfg-field">
            <label class="cfg-label">最短语音 (ms) <span class="cfg-hint">(预设: {{ currentModelInfo?.minSpeechMs ?? 300 }})</span></label>
            <input class="cfg-input" type="number" :value="overrideVal('min_speech_ms')" @change="onOverride('min_speech_ms', $event.target.value)"
                   min="50" max="2000" step="50" :placeholder="String(currentModelInfo?.minSpeechMs ?? 300)" />
          </div>
        </details>
      </div>
    </template>

    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :node="node" :input-ports="inputPorts" :output-ports="outputPorts" />
    </template>
    <template v-if="activeTab === 'io-mgmt' && editMode">
      <NodeIOMgmt :node="node" :edit-mode="editMode" :input-ports="inputPorts" :output-ports="outputPorts" @toggle-port="onTogglePort" />
    </template>
    <template v-if="activeTab === 'log'">
      <NodeLogView :logs="logs" />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { usePresetsStore } from '@/stores/presets'
import NodeIODataView from './NodeIODataView.vue'
import NodeIOMgmt from './NodeIOMgmt.vue'
import NodeLogView from './NodeLogView.vue'

const props = defineProps({
  node: { type: Object, required: true },
  status: { type: String, default: 'pending' },
  activeTab: { type: String, default: 'detail' },
  editMode: { type: Boolean, default: false },
  summary: { type: String, default: '' },
  progress: { type: Number, default: null },
  data: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
  logs: { type: Array, default: () => [] },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] }
})

const editorStore = useEditorStore()
const presetsStore = usePresetsStore()
presetsStore.initVad()

const statusLabel = computed(() => {
  const map = { pending: '等待音频', processing: '分句中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

// ── 预设选择 ──
const selectedModelKey = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return `${cfg.platform_id}/${cfg.model_id}`
  return ''
})

const displayPresetName = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getVadLabel(cfg.platform_id, cfg.model_id)
  return '未选择预设'
})

const currentModelInfo = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) {
    return presetsStore.vadAllModels.find(m => m.platformId === cfg.platform_id && m.modelId === cfg.model_id) || null
  }
  return null
})

// ── Override helpers ──
function overrideVal(key) {
  const cfg = props.config || props.node?.config || {}
  const ov = cfg.overrides || {}
  return ov[key] != null ? ov[key] : ''
}

function onOverride(key, rawVal) {
  const cfg = props.config || props.node?.config || {}
  const overrides = { ...(cfg.overrides || {}) }
  if (rawVal === '' || rawVal === undefined) {
    delete overrides[key]
  } else {
    overrides[key] = parseInt(rawVal)
  }
  editorStore.updateConfigImmediate(props.node.id, { ...cfg, overrides })
}

function onModelChange(e) {
  const [platformId, modelId] = e.target.value.split('/')
  const cfg = props.config || props.node?.config || {}
  editorStore.updateConfigImmediate(props.node.id, {
    platform_id: platformId,
    model_id: modelId,
    overrides: cfg.overrides || {},
  })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}
</script>

<style scoped>
.vad-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.model-tag {
  font-size: 8px; font-family: 'Space Grotesk', sans-serif;
  color: #adc7ff; background: rgba(173,199,255,0.08); padding: 1px 5px; border-radius: 9999px;
  margin-left: auto; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }

.proc-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #adc7ff; padding: 4px 0; }
.proc-icon { font-size: 14px; color: #4a8eff; }

.done-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #c1c6d7; padding: 4px 0; }
.done-icon { font-size: 14px; color: #4edea3; }

/* ── Config Tab ── */
.vad-config { padding: 4px 0; }
.vad-config .cfg-field { margin-bottom: 8px; }
.vad-config .cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.vad-config .cfg-hint { font-size: 8px; color: #64748b; }
.vad-config .cfg-select, .vad-config .cfg-input {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.vad-config .cfg-select:focus, .vad-config .cfg-input:focus { border-color: #4a8eff; }
.vad-config .cfg-overrides { margin-top: 10px; }
.vad-config .cfg-summary {
  font-size: 10px; color: #adc7ff; cursor: pointer; padding: 4px 0;
  border-bottom: 1px solid rgba(65,71,84,0.2); margin-bottom: 8px;
}
</style>
