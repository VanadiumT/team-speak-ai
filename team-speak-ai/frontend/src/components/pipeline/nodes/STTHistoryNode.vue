<template>
  <div class="stt-hist-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span v-if="isMatched" class="match-badge">★ 触发</span>
      </div>

      <div class="kw-bar" v-if="(config?.keywords || []).length">
        <span v-for="kw in (config?.keywords || [])" :key="kw" class="kw-chip" :class="{ hit: data?.trigger_keyword === kw }">{{ kw }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待文本片段...</div>

      <div v-if="status === 'processing'" class="process-hint">
        <span class="material-symbols-outlined spin-icon">sync</span>
        <span>判断中...</span>
      </div>

      <div v-if="status === 'completed' && isMatched" class="match-info">
        <span class="material-symbols-outlined match-icon">bolt</span>
        <span>关键词 "{{ data?.trigger_keyword }}" 匹配!</span>
        <div class="trigger-msg">→ 触发 ContextBuild</div>
      </div>

      <div v-if="status === 'completed' && !isMatched && data?.condition_result !== undefined" class="skip-info">
        <span>无关键词匹配 · 继续监听</span>
      </div>

      <div class="hist-count" v-if="(data?.history || []).length">
        历史 {{ data.history.length || 0 }}/{{ config?.max_entries || 20 }} 条
      </div>
      <div v-if="status === 'error'" class="error-text">{{ summary || '处理失败' }}</div>
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

const isMatched = computed(() => props.data?.condition_result === 'matched')
const isSkipped = computed(() => props.data?.condition_result === 'skipped')

const statusLabel = computed(() => {
  if (props.status === 'completed' && isMatched.value) return '已触发'
  if (props.status === 'completed' && isSkipped.value) return '已跳过'
  const map = { pending: '等待中', processing: '判断中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'max_entries', label: '最大保留条数', type: 'range', min: 5, max: 100, step: 5 },
  { key: 'context_window', label: '上下文窗口 (tokens)', type: 'number', min: 1024, max: 256000, placeholder: '128000' }
]


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
.stt-hist-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #ef6719; animation: pulse 1.5s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.match-badge {
  font-size: 8px; font-family: 'Space Grotesk', sans-serif; font-weight: 600;
  color: #ef6719; background: rgba(239,103,25,0.15); padding: 1px 5px; border-radius: 9999px;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.kw-bar { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 6px; }
.kw-chip {
  padding: 1px 6px; border-radius: 9999px;
  font-size: 8px; font-family: 'Space Grotesk', sans-serif; font-weight: 500;
  background: rgba(255,182,149,0.08); border: 1px solid rgba(255,182,149,0.2); color: #c1c6d7;
}
.kw-chip.hit {
  background: rgba(239,103,25,0.2); border-color: #ef6719; color: #ffb695;
  animation: keywordPulse 1.5s ease-in-out 2;
}
@keyframes keywordPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }

.process-hint { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #ffb695; }
.spin-icon { font-size: 14px; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.match-info { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 0; }
.match-icon { font-size: 18px; color: #ef6719; }
.trigger-msg { font-size: 9px; color: #4a8eff; }

.skip-info { font-size: 10px; color: #64748b; text-align: center; padding: 6px 0; }

.hist-count { font-size: 9px; color: #8b90a0; text-align: right; margin-top: 4px; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
