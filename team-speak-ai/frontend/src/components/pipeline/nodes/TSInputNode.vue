<template>
  <div class="ts-input-body">
    <!-- Flow Mode + detail tab -->
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status === 'listening' ? 'listening' : status" />
        <span class="status-text">{{ statusLabel }}</span>
      </div>

      <div class="audio-info">
        <div class="info-row">
          <span class="info-key">缓冲</span>
          <span class="info-val">{{ data?.buffer_mb ? data.buffer_mb.toFixed(1) + ' MB' : '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-key">采样率</span>
          <span class="info-val">{{ config?.sample_rate || 16000 }} Hz</span>
        </div>
        <div class="info-row">
          <span class="info-key">通道</span>
          <span class="info-val">{{ (config?.channels || 1) === 1 ? '单声道' : config?.channels + 'ch' }}</span>
        </div>
        <div class="info-row">
          <span class="info-key">最大缓冲</span>
          <span class="info-val">{{ formatBytes(config?.max_buffer_bytes || 10485760) }}</span>
        </div>
      </div>

      <div class="bus-hint">→ AudioBus → stt_listen</div>
      <div v-if="status === 'error'" class="error-text">{{ summary || '音频采集异常' }}</div>
    </template>

    <!-- Edit Mode: config tab -->
    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="node.config || {}" :fields="configFields" :readonly="false" @update="onUpdate" />
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
  const map = { pending: '等待中', listening: '收集中', processing: '处理中', error: '异常' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'max_buffer_bytes', label: '最大缓冲', type: 'select', options: [
    { value: 5242880, label: '5 MB' },
    { value: 10485760, label: '10 MB' },
    { value: 20971520, label: '20 MB' },
    { value: 52428800, label: '50 MB' },
  ]},
  { key: 'sample_rate', label: '采样率 (Hz)', type: 'select', options: [
    { value: 8000, label: '8000' },
    { value: 16000, label: '16000' },
    { value: 22050, label: '22050' },
    { value: 44100, label: '44100' },
    { value: 48000, label: '48000' },
  ]},
  { key: 'channels', label: '声道', type: 'chip-toggle', options: [
    { value: 1, label: '单声道' },
    { value: 2, label: '立体声' },
  ]},
]


function onUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

function formatBytes(bytes) {
  if (!bytes) return '10 MB'
  if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / 1048576).toFixed(0) + ' MB'
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
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.audio-info { margin-bottom: 4px; }
.info-row { display: flex; justify-content: space-between; padding: 2px 0; }
.info-key { font-size: 9px; color: #64748b; }
.info-val { font-size: 10px; color: #c1c6d7; font-family: 'Space Grotesk', sans-serif; }

.bus-hint {
  font-size: 9px; color: #4a8eff; text-align: center;
  padding: 4px 0; border-top: 1px solid rgba(65,71,84,0.3);
  margin-top: 4px;
}

.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
