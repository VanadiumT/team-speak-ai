<template>
  <div class="ocr-body">
    <!-- Flow Mode + detail tab -->
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
      </div>

      <div v-if="status === 'processing'" class="mini-bar-wrap">
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
        <span class="mini-pct">{{ Math.round((progress ?? 0) * 100) }}%</span>
      </div>

      <div v-if="status === 'completed'" class="output-preview">
        <div class="preview-label">OCR 文本</div>
        <div class="preview-text">{{ (data?.text || summary || '无内容').slice(0, 80) }}{{ (data?.text || '').length > 80 ? '...' : '' }}</div>
        <div class="preview-meta" v-if="data?.confidence != null">
          置信度: {{ (data.confidence * 100).toFixed(0) }}% · 区域: {{ data?.region_count ?? '-' }}
        </div>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待图片...</div>
      <div v-if="status === 'error'" class="error-text">{{ summary || 'OCR 识别失败' }}</div>
    </template>

    <!-- Edit Mode: config tab -->
    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="node.config || {}" :fields="configFields" :readonly="false" @update="onUpdate" />
    </template>

    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :inputs="inputRuntime" :outputs="outputRuntime" />
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
import NodeConfigForm from './NodeConfigForm.vue'
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

const statusLabel = computed(() => {
  const map = { pending: '待命', processing: '识别中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'engine', label: '引擎', type: 'chip-toggle', options: [
    { value: 'easyocr', label: 'EasyOCR' }, { value: 'paddleocr', label: 'PaddleOCR' }
  ]},
  { key: 'language', label: '识别语言', type: 'checkbox-group', options: [
    { value: 'zh', label: '中文' }, { value: 'en', label: '英文' }, { value: 'ja', label: '日文' }, { value: 'ko', label: '韩文' }
  ]},
  { key: 'confidence_threshold', label: '置信度阈值', type: 'range', min: 0, max: 1, step: 0.05 }
]

const inputRuntime = computed(() => ({
  'ocr-in': props.data?.file_name ? `来源: ${props.data.file_name}` : '(无数据)'
}))
const outputRuntime = computed(() => ({
  'ocr-out': props.data?.text || '(无数据)',
  'meta-confidence': props.data?.confidence != null ? String(props.data.confidence) : '(无数据)',
  'meta-region-count': props.data?.region_count != null ? String(props.data.region_count) : '(无数据)'
}))

function onUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
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
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
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
</style>
