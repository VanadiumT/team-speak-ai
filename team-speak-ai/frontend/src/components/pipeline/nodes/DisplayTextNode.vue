<!--
  DisplayTextNode — 文本显示节点 body
-->
<template>
  <div class="display-text-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div v-if="status === 'completed'" class="text-preview">
        <div class="text-content">{{ displayText || '(空)' }}</div>
      </div>
      <div v-else-if="status === 'processing'" class="text-waiting">
        <span class="material-symbols-outlined spin" style="font-size: 14px; color: #adc7ff;">progress_activity</span>
        <span>处理中...</span>
      </div>
      <div v-else class="text-waiting">
        <span class="material-symbols-outlined" style="font-size: 14px; color: #64748b;">text_fields</span>
        <span>{{ config?.mode === 'static' ? '显示文本' : '等待输入...' }}</span>
      </div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="config || {}" :fields="configFields" :readonly="false" @update="onConfigUpdate" />
    </template>

    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :inputs="inputPorts" :outputs="outputPorts" />
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
  data: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
  logs: { type: Array, default: () => [] },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] },
})

const editorStore = useEditorStore()

const displayText = computed(() => {
  return props.data?.text || props.config?.text || ''
})

const configFields = [
  { key: 'mode', label: '模式', type: 'chip-toggle', options: [
    { value: 'passthrough', label: '透传' },
    { value: 'static', label: '静态' },
  ]},
  { key: 'text', label: '文本内容', type: 'textarea', placeholder: '输入要显示的文本...' },
]

function onConfigUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}
</script>

<style scoped>
.display-text-body { padding: 4px 0; }
.text-preview {
  padding: 6px 8px; font-size: 11px; color: #c1c6d7;
  max-height: 80px; overflow-y: auto;
}
.text-content {
  white-space: pre-wrap; word-break: break-word;
  line-height: 1.5; font-family: 'Space Grotesk', monospace;
  font-size: 10px;
}
.text-waiting {
  display: flex; align-items: center; gap: 6px;
  padding: 8px; font-size: 11px; color: #64748b;
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
