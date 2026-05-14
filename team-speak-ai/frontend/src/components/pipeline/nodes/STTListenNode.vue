<template>
  <div class="stt-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="model-tag">{{ displayModelName }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待触发信号...</div>

      <div v-if="status === 'processing'" class="recog-preview">
        <span class="material-symbols-outlined recog-icon">graphic_eq</span>
        <span class="recog-text">{{ (data?.text || summary || '转写中...').slice(0, 80) }}</span>
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
      </div>

      <div v-if="status === 'completed'" class="result-text">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>{{ (data?.text || '').slice(0, 120) }}{{ (data?.text || '').length > 120 ? '...' : '' }}</span>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || 'STT 转写失败' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="stt-config">
        <div class="cfg-field">
          <label class="cfg-label">STT 模型</label>
          <select class="cfg-select" :value="selectedModelKey" @change="onModelChange">
            <option v-if="!selectedModelKey" value="" disabled>选择模型...</option>
            <option v-for="m in presetsStore.sttAllModels"
                    :key="m.platformId + '/' + m.modelId"
                    :value="m.platformId + '/' + m.modelId">
              {{ m.label }}
            </option>
          </select>
        </div>

        <details class="cfg-overrides">
          <summary class="cfg-summary">覆盖预设值 (可选)</summary>
          <div class="cfg-field">
            <label class="cfg-label">语言</label>
            <select class="cfg-select" :value="overrideVal('language')" @change="onOverride('language', $event.target.value)">
              <option value="">预设: {{ currentModelInfo?.language || 'auto' }}</option>
              <option value="auto">auto</option>
              <option value="zh">zh</option>
              <option value="en">en</option>
            </select>
          </div>
          <div class="cfg-field">
            <label class="cfg-label">采样率 (Hz)</label>
            <select class="cfg-select" :value="overrideVal('sample_rate')" @change="onOverride('sample_rate', $event.target.value)">
              <option value="">预设: {{ currentModelInfo?.sampleRate || 16000 }}</option>
              <option :value="8000">8000</option>
              <option :value="16000">16000</option>
              <option :value="48000">48000</option>
            </select>
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
  const map = { pending: '等待中', processing: '转写中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

// ── 预设选择 ──
const selectedModelKey = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return `${cfg.platform_id}/${cfg.model_id}`
  return ''
})

const currentModelInfo = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getSttModelInfo(cfg.platform_id, cfg.model_id)
  return null
})

const displayModelName = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getSttLabel(cfg.platform_id, cfg.model_id)
  return cfg.engine || 'sensevoice'
})

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
  } else if (key === 'sample_rate') {
    overrides[key] = parseInt(rawVal)
  } else {
    overrides[key] = rawVal
  }
  editorStore.updateConfigImmediate(props.node.id, { ...cfg, overrides })
}

function onModelChange(e) {
  const [platformId, modelId] = e.target.value.split('/')
  const cfg = props.config || props.node?.config || {}
  editorStore.updateConfigImmediate(props.node.id, {
    ...cfg,
    platform_id: platformId,
    model_id: modelId,
  })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}
</script>

<style scoped>
.stt-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 0.8s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.model-tag {
  font-size: 8px; font-family: 'Space Grotesk', sans-serif;
  color: #adc7ff; background: rgba(173,199,255,0.08); padding: 1px 5px; border-radius: 9999px;
  margin-left: auto;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.recog-preview { display: flex; align-items: center; gap: 4px; margin-bottom: 6px; flex-wrap: wrap; }
.recog-icon { font-size: 14px; color: #4a8eff; }
.recog-text { font-size: 10px; color: #e0e2ed; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-bar { width: 100%; height: 2px; background: #31353d; border-radius: 1px; overflow: hidden; }
.mini-bar-fill { height: 100%; background: #4a8eff; border-radius: 1px; transition: width 0.3s; }

.result-text {
  display: flex; align-items: flex-start; gap: 4px;
  font-size: 10px; color: #c1c6d7; padding: 4px 0;
}
.done-icon { font-size: 14px; color: #4edea3; flex-shrink: 0; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }

/* ── Config Tab ── */
.stt-config { padding: 4px 0; }
.stt-config .cfg-field { margin-bottom: 8px; }
.stt-config .cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.stt-config .cfg-select {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.stt-config .cfg-select:focus { border-color: #4a8eff; }
.stt-config .cfg-overrides { margin-top: 10px; }
.stt-config .cfg-summary {
  font-size: 10px; color: #adc7ff; cursor: pointer; padding: 4px 0;
  border-bottom: 1px solid rgba(65,71,84,0.2); margin-bottom: 8px;
}
</style>
