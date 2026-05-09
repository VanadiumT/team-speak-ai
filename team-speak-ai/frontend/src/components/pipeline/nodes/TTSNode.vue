<template>
  <div class="tts-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待文本...</div>

      <div v-if="status === 'processing'" class="synth-info">
        <span class="material-symbols-outlined synth-icon">record_voice_over</span>
        <span>合成中</span>
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
        <div class="seg-count">句 {{ data?.current_segment ?? 0 }}/{{ data?.total_segments ?? '-' }}</div>
      </div>

      <div v-if="status === 'completed'" class="done-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>{{ data?.total_segments ?? 0 }} 句 · {{ formatDuration(data?.total_duration) }}</span>
        <div class="engine-tag">{{ config?.engine || 'edge' }} · {{ config?.voice || 'YunxiNeural' }}</div>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || '合成失败' }}</div>
    </template>

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
  const map = { pending: '等待文本', processing: '合成中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'engine', label: '合成引擎', type: 'chip-toggle', options: [
    { value: 'edge', label: 'Edge' }, { value: 'minimax', label: 'MiniMax' }
  ]},
  { key: 'voice', label: '音色', type: 'select', options: [
    { value: 'zh-CN-YunxiNeural', label: 'Yunxi (男)' },
    { value: 'zh-CN-XiaoxiaoNeural', label: 'Xiaoxiao (女)' },
    { value: 'zh-CN-YunyangNeural', label: 'Yunyang (男)' }
  ]},
  { key: 'speed', label: '语速', type: 'range', min: 0.5, max: 2.0, step: 0.1 }
]


function onUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

function formatDuration(sec) {
  if (!sec) return '0s'
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return m ? `${m}m${s}s` : `${s}s`
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
</style>
