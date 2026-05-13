<template>
  <div class="ts-input-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status === 'listening' ? 'listening' : status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="model-tag">{{ displayPresetName }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待触发信号...</div>

      <div v-if="status === 'processing'" class="proc-info">
        <span class="material-symbols-outlined proc-icon">graphic_eq</span>
        <span>{{ summary || '接收中...' }}</span>
      </div>

      <div v-if="status === 'completed'" class="done-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>{{ (data?.total_bytes ? (data.total_bytes / 1024).toFixed(1) + ' KB' : '') }} · {{ data?.frames ?? 0 }} 帧</span>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || '音频采集异常' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="ts-config">
        <div class="cfg-field">
          <label class="cfg-label">桥接连接</label>
          <select class="cfg-select" :value="selectedModelKey" @change="onModelChange">
            <option v-if="!selectedModelKey" value="" disabled>选择桥接配置...</option>
            <option v-for="m in presetsStore.tsAllModels"
                    :key="m.platformId + '/' + m.modelId"
                    :value="m.platformId + '/' + m.modelId">
              {{ m.label }}
            </option>
          </select>
        </div>

        <details class="cfg-overrides">
          <summary class="cfg-summary">覆盖音频参数 (可选)</summary>
          <div class="cfg-field">
            <label class="cfg-label">最大缓冲</label>
            <select class="cfg-select" :value="overrideVal('max_buffer_bytes')" @change="onOverride('max_buffer_bytes', $event.target.value)">
              <option value="">默认: 10 MB</option>
              <option :value="5242880">5 MB</option>
              <option :value="10485760">10 MB</option>
              <option :value="20971520">20 MB</option>
              <option :value="52428800">50 MB</option>
            </select>
          </div>
          <div class="cfg-field">
            <label class="cfg-label">采样率 (Hz)</label>
            <select class="cfg-select" :value="overrideVal('sample_rate')" @change="onOverride('sample_rate', $event.target.value)">
              <option value="">默认: 16000</option>
              <option :value="8000">8000</option>
              <option :value="16000">16000</option>
              <option :value="22050">22050</option>
              <option :value="44100">44100</option>
              <option :value="48000">48000</option>
            </select>
          </div>
          <div class="cfg-field">
            <label class="cfg-label">声道</label>
            <select class="cfg-select" :value="overrideVal('channels')" @change="onOverride('channels', $event.target.value)">
              <option value="">默认: 单声道</option>
              <option :value="1">单声道</option>
              <option :value="2">立体声</option>
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
presetsStore.initTs()

const statusLabel = computed(() => {
  const map = { pending: '等待中', listening: '收集中', processing: '处理中', error: '异常' }
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
  if (cfg.platform_id && cfg.model_id) return presetsStore.getTsLabel(cfg.platform_id, cfg.model_id)
  return '未选择桥接'
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
  } else if (key === 'sample_rate' || key === 'max_buffer_bytes' || key === 'channels') {
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
.ts-input-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.listening { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.processing { background: #4a8eff; animation: pulse 1.5s infinite; }
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
.ts-config { padding: 4px 0; }
.ts-config .cfg-field { margin-bottom: 8px; }
.ts-config .cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.ts-config .cfg-select {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.ts-config .cfg-select:focus { border-color: #4a8eff; }
.ts-config .cfg-overrides { margin-top: 10px; }
.ts-config .cfg-summary {
  font-size: 10px; color: #adc7ff; cursor: pointer; padding: 4px 0;
  border-bottom: 1px solid rgba(65,71,84,0.2); margin-bottom: 8px;
}
</style>
