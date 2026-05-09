<template>
  <div class="llm-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="model-tag">{{ config?.model || 'gpt-4-turbo' }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待上游上下文...</div>

      <!-- PROCESSING: streaming text -->
      <div v-if="status === 'processing'" class="stream-area">
        <div class="mini-bar-wrap">
          <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
        </div>
        <div class="stream-text">
          {{ (data?.content_full || summary || '生成中...').slice(0, 120) }}
          <span class="stream-cursor" v-if="status === 'processing'">█</span>
        </div>
      </div>

      <!-- COMPLETED: response summary -->
      <div v-if="status === 'completed'" class="response-area">
        <div class="response-text">{{ (data?.response || summary || '').slice(0, 120) }}{{ (data?.response || '').length > 120 ? '...' : '' }}</div>
        <div class="response-meta">
          <span v-if="data?.input_tokens">入 {{ data.input_tokens }} tk</span>
          <span v-if="data?.output_tokens">出 {{ data.output_tokens }} tk</span>
          <span v-if="data?.model">· {{ data.model }}</span>
        </div>
        <div class="reasoning-hint" v-if="data?.reasoning">含思考过程</div>
        <div class="trigger-hint">→ 触发 TTS</div>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || 'LLM 调用失败' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm :config="node.config || {}" :fields="configFields" :readonly="false" @update="onUpdate" />
    </template>
    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :inputs="ioInputs" :outputs="ioOutputs" />
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
  const map = { pending: '等待中', processing: '生成中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'model', label: '模型', type: 'chip-toggle', options: [
    { value: 'gpt-4-turbo', label: 'GPT-4T' }, { value: 'gpt-4o', label: 'GPT-4o' }, { value: 'deepseek-v3', label: 'DeepSeek-V3' }
  ]},
  { key: 'temperature', label: 'Temperature', type: 'range', min: 0, max: 2, step: 0.05 },
  { key: 'max_tokens', label: 'Max Tokens', type: 'number', min: 64, max: 32768, placeholder: '2048' },
  { key: 'streaming', label: '流式输出', type: 'switch' }
]

const ioInputs = computed(() => ({
  'llm-in': props.data?.message_count ? `${props.data.message_count} 条消息, ${props.data.total_tokens || '?'} tokens` : '(无数据)'
}))
const ioOutputs = computed(() => ({
  'llm-out': props.data?.response ? props.data.response.slice(0, 80) + '...' : '(无数据)',
  'meta-token-count': props.data?.total_tokens ? `入 ${props.data.input_tokens || '?'} + 出 ${props.data.output_tokens || '?'} = ${props.data.total_tokens}` : '(无数据)',
  'meta-reasoning': props.data?.reasoning ? props.data.reasoning.slice(0, 60) + '...' : '(无)',
  'meta-model': props.data?.model || props.config?.model || '(未知)'
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
.llm-body { padding: 2px 0; }
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
  margin-left: auto;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.mini-bar-wrap { margin-bottom: 4px; }
.mini-bar { height: 2px; background: #31353d; border-radius: 1px; overflow: hidden; }
.mini-bar-fill { height: 100%; background: #4a8eff; border-radius: 1px; transition: width 0.3s; }

.stream-area { margin-bottom: 4px; }
.stream-text {
  font-size: 10px; color: #e0e2ed; line-height: 1.5; word-break: break-all;
  max-height: 72px; overflow: hidden;
}
.stream-cursor {
  color: #4a8eff; animation: blink 0.8s step-end infinite;
}
@keyframes blink { 0%,50% { opacity: 1; } 51%,100% { opacity: 0; } }

.response-area { margin-bottom: 4px; }
.response-text { font-size: 10px; color: #e0e2ed; line-height: 1.4; max-height: 60px; overflow: hidden; word-break: break-all; }
.response-meta { display: flex; gap: 4px; font-size: 9px; color: #64748b; font-family: 'Space Grotesk', sans-serif; margin-top: 2px; }
.reasoning-hint { font-size: 9px; color: #ffb695; }
.trigger-hint { font-size: 9px; color: #4a8eff; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
