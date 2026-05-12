<template>
  <div class="ctx-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待触发信号...</div>

      <div v-if="status === 'processing'" class="build-info">
        <div class="build-item" v-for="src in inputSources" :key="src.key">
          <span class="material-symbols-outlined check-icon" :class="{ ready: src.ready }">{{ src.ready ? 'check_circle' : 'radio_button_unchecked' }}</span>
          <span class="src-label">{{ src.label }}</span>
          <span class="src-tokens" v-if="src.tokens">{{ src.tokens }} tk</span>
        </div>
        <div class="total-tokens" v-if="totalTokens">总计: {{ totalTokens }} / {{ config?.max_context_length || 4096 }} tokens</div>
      </div>

      <div v-if="status === 'completed'" class="result-info">
        <div class="result-summary">
          <span class="material-symbols-outlined done-icon">check_circle</span>
          <span>{{ data?.fragment_count ?? 0 }} 个片段, {{ data?.total_chars ?? 0 }} 字符, {{ data?.message_count ?? 0 }} 条消息</span>
        </div>
        <div v-if="data?.user_message" class="result-content">
          <pre class="result-pre">{{ data.user_message }}</pre>
        </div>
        <div v-if="data?.messages" class="result-messages">
          <div v-for="(msg, i) in data.messages" :key="i" class="msg-block">
            <span class="msg-role">{{ msg.role }}</span>
            <pre class="msg-content">{{ msg.content }}</pre>
          </div>
        </div>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || '构建失败' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="node.config || {}" :fields="configFields" :readonly="false" @update="onUpdate" />
    </template>
    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :node="node" :input-ports="inputPorts" :output-ports="outputPorts" />
    </template>
    <template v-if="activeTab === 'io-mgmt' && editMode">
      <NodeIOMgmt :node="node" :edit-mode="editMode" :input-ports="inputPorts" :output-ports="outputPorts"
        @toggle-port="onTogglePort" @add-port="onAddPort" @remove-port="onRemovePort" />
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
  const map = { pending: '等待触发', processing: '构建中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'max_context_length', label: '最大上下文 (tokens)', type: 'number', min: 512, max: 128000, placeholder: '4096' }
]

const inputSources = computed(() => {
  const portIds = props.node.config?._repeatable_ports?.ctx || ['ctx-in1']
  const labels = props.node.config?._port_labels || {}
  return portIds.map((id, i) => ({
    key: id,
    label: labels[id] || `信息${i + 1}`,
    ready: !!(props.data?.[id]),
    tokens: props.data?.[`${id}_tokens`],
  }))
})

const totalTokens = computed(() => props.data?.total_tokens)


function onUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

function onAddPort(group) {
  editorStore.addRepeatablePort(props.node.id, group)
}

function onRemovePort(portId) {
  editorStore.removeRepeatablePort(props.node.id, portId)
}
</script>

<style scoped>
.ctx-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.build-info { display: flex; flex-direction: column; gap: 3px; }
.build-item { display: flex; align-items: center; gap: 4px; font-size: 10px; }
.check-icon { font-size: 14px; color: #414754; }
.check-icon.ready { color: #4edea3; }
.src-label { color: #c1c6d7; flex: 1; }
.src-tokens { font-size: 9px; color: #64748b; font-family: 'Space Grotesk', sans-serif; }
.total-tokens { font-size: 9px; color: #adc7ff; font-family: 'Space Grotesk', sans-serif; text-align: right; margin-top: 2px; }

.result-info { display: flex; flex-direction: column; gap: 6px; }
.result-summary { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #4edea3; }
.done-icon { font-size: 16px; flex-shrink: 0; }
.result-content { }
.result-pre {
  font-size: 9px; color: #c1c6d7; white-space: pre-wrap; word-break: break-all;
  background: rgba(11,14,22,0.6); border-radius: 4px; padding: 6px 8px;
  max-height: 240px; overflow-y: auto; line-height: 1.5;
  font-family: 'Space Grotesk', sans-serif;
}
.result-messages { display: flex; flex-direction: column; gap: 4px; max-height: 300px; overflow-y: auto; }
.msg-block { background: rgba(11,14,22,0.6); border-radius: 4px; padding: 4px 6px; }
.msg-role {
  font-size: 8px; color: #ffb695; text-transform: uppercase;
  font-family: 'Space Grotesk', sans-serif; letter-spacing: 0.05em; margin-bottom: 2px; display: block;
}
.msg-content {
  font-size: 9px; color: #8b90a0; white-space: pre-wrap; word-break: break-all;
  margin: 0; line-height: 1.4; max-height: 120px; overflow-y: auto;
  font-family: 'Space Grotesk', sans-serif;
}

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
