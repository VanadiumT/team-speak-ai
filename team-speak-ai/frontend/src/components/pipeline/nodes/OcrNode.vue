<template>
  <div class="ocr-body">
    <!-- Flow Mode + detail tab -->
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="model-tag">{{ displayModelName }}</span>
      </div>

      <div v-if="status === 'processing'" class="mini-bar-wrap">
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
        <span class="mini-pct">{{ Math.round((progress ?? 0) * 100) }}%</span>
      </div>

      <div v-if="status === 'completed'" class="output-preview">
        <div class="preview-label">OCR 文本</div>
        <div class="preview-text">{{ (data?.text || summary || '无内容').slice(0, 80) }}{{ (data?.text || '').length > 80 ? '...' : '' }}</div>
        <div class="preview-meta" v-if="data?.line_count != null">
          识别行数: {{ data.line_count }} · 引擎: {{ data?.provider || '-' }}
        </div>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待图片...</div>
      <div v-if="status === 'error'" class="error-text">{{ summary || 'OCR 识别失败' }}</div>
    </template>

    <!-- Edit Mode: config tab -->
    <template v-if="editMode && activeTab === 'config'">
      <div class="ocr-config">
        <div class="cfg-field">
          <label class="cfg-label">OCR 预设</label>
          <select class="cfg-select" :value="selectedModelKey" @change="onModelChange">
            <option v-if="!selectedModelKey" value="" disabled>选择预设...</option>
            <option v-for="m in presetsStore.ocrAllModels" :key="m.platformId + '/' + m.modelId"
                    :value="m.platformId + '/' + m.modelId">
              {{ m.label }}
            </option>
          </select>
        </div>

        <details class="cfg-overrides" :open="hasOverrides">
          <summary class="cfg-summary">覆盖预设值 (可选)</summary>
          <div class="cfg-field">
            <label class="cfg-label">置信度阈值 <span class="cfg-hint">(预设: {{ currentModelInfo?.confidenceThreshold ?? '-' }})</span></label>
            <input class="cfg-input" type="range" :value="overrideVal('confidence_threshold') || (currentModelInfo?.confidenceThreshold ?? 0.3)"
                   @input="onOverride('confidence_threshold', $event.target.value)" min="0" max="1" step="0.05" />
            <span class="cfg-range-val">{{ overrideVal('confidence_threshold') || (currentModelInfo?.confidenceThreshold ?? 0.3) }}</span>
          </div>
          <div class="cfg-field">
            <label class="cfg-label cfg-check-label" @click="onOverride('gpu', !(overrideVal('gpu') ?? currentModelInfo?.gpu))">
              <input type="checkbox" :checked="overrideVal('gpu') ?? currentModelInfo?.gpu ?? false"
                     @change="onOverride('gpu', $event.target.checked)" />
              使用 GPU 加速 <span class="cfg-hint">(预设: {{ currentModelInfo?.gpu ? 'GPU' : 'CPU' }})</span>
            </label>
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
  const map = { pending: '待命', processing: '识别中', completed: '已完成', error: '错误' }
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
  if (cfg.platform_id && cfg.model_id) return presetsStore.getOcrModelInfo(cfg.platform_id, cfg.model_id)
  return null
})

const displayModelName = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getOcrLabel(cfg.platform_id, cfg.model_id)
  return '未配置预设'
})

const hasOverrides = computed(() => {
  const cfg = props.config || props.node?.config || {}
  const ov = cfg.overrides || {}
  return Object.keys(ov).length > 0
})

function overrideVal(key) {
  const cfg = props.config || props.node?.config || {}
  const ov = cfg.overrides || {}
  return ov[key] != null ? ov[key] : undefined
}

function onOverride(key, rawVal) {
  const cfg = props.config || props.node?.config || {}
  const overrides = { ...(cfg.overrides || {}) }
  let val
  if (rawVal === '' || rawVal === undefined || rawVal === 'undefined') {
    val = undefined
  } else if (key === 'gpu') {
    val = Boolean(rawVal)
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
.ocr-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 0.8s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.model-tag {
  font-size: 8px; font-family: 'Space Grotesk', sans-serif;
  color: #adc7ff; background: rgba(173,199,255,0.08); padding: 1px 5px; border-radius: 9999px;
  max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-left: auto;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.mini-bar-wrap { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.mini-bar { flex: 1; height: 3px; background: #31353d; border-radius: 2px; overflow: hidden; }
.mini-bar-fill { height: 100%; background: #adc7ff; border-radius: 2px; transition: width 0.3s; }
.mini-pct { font-size: 9px; font-family: 'Space Grotesk', sans-serif; color: #adc7ff; }

.output-preview { margin-top: 2px; }
.preview-label { font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
.preview-text { font-size: 10px; color: #e0e2ed; line-height: 1.4; word-break: break-all; }
.preview-meta { font-size: 9px; color: #64748b; margin-top: 2px; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }

/* ── Config Tab ── */
.ocr-config { padding: 4px 0; }
.cfg-field { margin-bottom: 8px; }
.cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.cfg-hint { font-size: 8px; color: #64748b; }
.cfg-select, .cfg-input {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.cfg-select:focus, .cfg-input:focus { border-color: #4a8eff; }
.cfg-input[type="range"] { padding: 2px 0; height: 20px; }
.cfg-range-val {
  font-size: 9px; color: #adc7ff; font-family: 'Space Grotesk', sans-serif;
  margin-left: 6px;
}
.cfg-check-label { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.cfg-check-label input { width: auto; }
.cfg-overrides { margin-top: 10px; }
.cfg-summary {
  font-size: 10px; color: #adc7ff; cursor: pointer; padding: 4px 0;
  border-bottom: 1px solid rgba(65,71,84,0.2); margin-bottom: 8px;
}
</style>
