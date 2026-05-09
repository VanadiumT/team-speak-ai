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

      <div v-if="status === 'completed'" class="done-info">
        <div class="done-row">
          <span class="material-symbols-outlined done-icon">check_circle</span>
          <span>{{ data?.message_count ?? 0 }} 条消息</span>
        </div>
        <div class="done-tokens">{{ totalTokens }} tokens</div>
        <div class="trigger-hint">→ 触发 LLM</div>
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
  const map = { pending: '等待触发', processing: '构建中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'max_context_length', label: '最大上下文 (tokens)', type: 'number', min: 512, max: 128000, placeholder: '4096' }
]

const inputSources = computed(() => [
  { key: 'skill', label: 'Skill Prompt', ready: !!(props.data?.has_skill_prompt || props.node.config?.skill_prompt), tokens: props.data?.skill_tokens },
  { key: 'ocr', label: 'OCR 文本', ready: !!(props.data?.has_ocr), tokens: props.data?.ocr_tokens },
  { key: 'stt', label: 'STT 历史', ready: !!(props.data?.has_stt), tokens: props.data?.stt_tokens },
  { key: 'history', label: '对话历史', ready: !!(props.data?.has_history), tokens: props.data?.history_tokens }
])

const totalTokens = computed(() => props.data?.total_tokens)


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

.done-info { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 0; }
.done-row { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #4edea3; }
.done-icon { font-size: 18px; }
.done-tokens { font-size: 9px; color: #64748b; font-family: 'Space Grotesk', sans-serif; }
.trigger-hint { font-size: 9px; color: #4a8eff; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
