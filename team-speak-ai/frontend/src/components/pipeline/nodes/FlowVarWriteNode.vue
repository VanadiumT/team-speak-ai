<!--
  FlowVarWriteNode — 写入流程参数节点 body
-->
<template>
  <div class="flow-var-write-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div v-if="status === 'completed'" class="var-preview">
        <span class="var-key">{{ data?.key || config?.key || '...' }}</span>
        <span class="var-eq">=</span>
        <span class="var-value">{{ formatValue(data?.value) }}</span>
        <span class="material-symbols-outlined var-check">check_circle</span>
      </div>
      <div v-else class="var-waiting">
        <span class="material-symbols-outlined" style="font-size: 14px; color: #64748b;">output</span>
        <span>等待写入...</span>
      </div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="config || {}" :fields="configFields" :readonly="false" @update="onConfigUpdate" />
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
  data: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
  logs: { type: Array, default: () => [] },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] },
})

const editorStore = useEditorStore()

const configFields = [
  { key: 'key', label: '参数 Key', type: 'text', placeholder: 'llm_response' },
  { key: 'merge_mode', label: '写入模式', type: 'select', options: [
    { value: 'overwrite', label: '覆盖' },
    { value: 'append', label: '追加 (列表)' },
  ]},
]

function onConfigUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

function formatValue(v) {
  if (v === null || v === undefined) return '(空)'
  if (typeof v === 'object') return JSON.stringify(v)
  const s = String(v)
  return s.length > 40 ? s.slice(0, 40) + '...' : s
}
</script>

<style scoped>
.flow-var-write-body { padding: 4px 0; }
.var-preview {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 8px; font-size: 11px; font-family: 'Space Grotesk', monospace;
}
.var-key { color: #adc7ff; font-weight: 600; }
.var-eq { color: #64748b; }
.var-value { color: #4edea3; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.var-check { font-size: 14px; color: #4edea3; }
.var-waiting {
  display: flex; align-items: center; gap: 6px;
  padding: 8px; font-size: 11px; color: #64748b;
}
</style>
