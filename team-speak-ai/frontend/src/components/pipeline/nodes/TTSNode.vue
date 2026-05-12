<template>
  <div class="tts-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="mode-badge">{{ streaming ? '流式' : '非流式' }}</span>
        <span class="model-tag">{{ displayModelName }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待文本...</div>

      <div v-if="status === 'processing'" class="synth-info">
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
        <div class="seg-count">{{ data?.current_segment ?? 0 }}/{{ data?.total_segments ?? 0 }} 句</div>
      </div>

      <div v-if="status === 'completed'" class="done-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>{{ data?.total_segments ?? 0 }} 句</span>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || '合成失败' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="tts-config">
        <div class="cfg-field">
          <label class="cfg-label">模型</label>
          <select class="cfg-select" :value="selectedModelKey" @change="onModelChange">
            <option v-if="!selectedModelKey" value="" disabled>选择模型...</option>
            <option v-for="m in presetsStore.ttsAllModels" :key="m.platformId + '/' + m.modelId"
                    :value="m.platformId + '/' + m.modelId">
              {{ m.label }}
            </option>
          </select>
        </div>

        <details class="cfg-overrides">
          <summary class="cfg-summary">覆盖预设值 (可选)</summary>
          <div class="cfg-field">
            <label class="cfg-label">语速 <span class="cfg-hint">(预设: {{ currentModelInfo?.speed ?? '-' }})</span></label>
            <input class="cfg-input" type="number" :value="overrideVal('speed')" @change="onOverride('speed', $event.target.value)"
                   min="0.5" max="2" step="0.1" :placeholder="String(currentModelInfo?.speed ?? '')" />
          </div>
          <div class="cfg-field">
            <label class="cfg-label">音色 <span class="cfg-hint">(预设: {{ currentModelInfo?.voiceId ?? '-' }})</span></label>
            <input class="cfg-input" type="text" :value="overrideVal('voice_id')" @change="onOverride('voice_id', $event.target.value)"
                   :placeholder="currentModelInfo?.voiceId || ''" />
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

const statusLabel = computed(() => {
  const map = { pending: '等待文本', processing: '合成中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

// ── 模型配置 ──
const displayModelName = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getTtsLabel(cfg.platform_id, cfg.model_id)
  if (cfg.engine) return `${cfg.engine} · ${cfg.voice || ''}`
  return '未选择模型'
})

const selectedModelKey = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return `${cfg.platform_id}/${cfg.model_id}`
  return ''
})

const currentModelInfo = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) {
    return presetsStore.ttsAllModels.find(m => m.platformId === cfg.platform_id && m.modelId === cfg.model_id) || null
  }
  return null
})

const streaming = computed(() => {
  const cfg = props.config || props.node?.config || {}
  const ov = cfg.overrides || {}
  if ('streaming' in ov) return !!ov.streaming
  return currentModelInfo.value?.streaming !== false
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
  let val
  if (rawVal === '' || rawVal === undefined) {
    val = undefined
  } else if (key === 'voice_id') {
    val = rawVal
  } else {
    val = parseFloat(rawVal)
  }
  if (val === undefined || (typeof val === 'number' && isNaN(val))) {
    delete overrides[key]
  } else {
    overrides[key] = val
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
.tts-body { padding: 2px 0; }
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
  max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mode-badge {
  font-size: 8px; padding: 1px 5px; border-radius: 9999px; margin-left: auto;
  background: rgba(78,222,163,0.1); color: #4edea3;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.synth-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #adc7ff; flex-wrap: wrap; }
.synth-icon { font-size: 16px; }
.mini-bar { flex: 1; height: 3px; background: #31353d; border-radius: 2px; overflow: hidden; min-width: 40px; }
.mini-bar-fill { height: 100%; background: #adc7ff; border-radius: 2px; transition: width 0.3s; }
.seg-count { font-size: 9px; color: #8b90a0; }

.done-info { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 0; }
.done-icon { font-size: 20px; color: #4edea3; }
.engine-tag {
  font-size: 9px; font-family: 'Space Grotesk', sans-serif;
  color: #8b90a0; background: rgba(139,144,160,0.1); padding: 1px 6px; border-radius: 9999px;
}

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }

/* ── Config Tab ── */
.tts-config { padding: 4px 0; }
.cfg-field { margin-bottom: 8px; }
.cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.cfg-hint { font-size: 8px; color: #64748b; }
.cfg-select, .cfg-input {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.cfg-select:focus, .cfg-input:focus { border-color: #4a8eff; }
.cfg-overrides { margin-top: 10px; }
.cfg-summary {
  font-size: 10px; color: #adc7ff; cursor: pointer; padding: 4px 0;
  border-bottom: 1px solid rgba(65,71,84,0.2); margin-bottom: 8px;
}
</style>
