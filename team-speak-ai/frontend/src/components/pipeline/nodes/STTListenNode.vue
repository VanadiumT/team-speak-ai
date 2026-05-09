<template>
  <div class="stt-listen-body">
    <!-- Flow Mode + detail tab -->
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="keyword-dot" v-if="status === 'listening'" />
      </div>

      <!-- Config summary (always visible in flow mode) -->
      <div class="config-chips">
        <span class="config-chip" v-for="kw in (config?.keywords || [])" :key="kw">{{ kw }}</span>
        <span class="config-chip engine">{{ config?.engine || 'sensevoice' }}</span>
      </div>

      <!-- PROCESSING: temporary recognition state -->
      <div v-if="status === 'processing'" class="recog-preview">
        <span class="material-symbols-outlined recog-icon">graphic_eq</span>
        <span class="recog-text">{{ (data?.text || summary || '识别中...').slice(0, 60) }}</span>
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
      </div>

      <!-- COMPLETED/LISTENING: recent outputs -->
      <div class="recent-outputs" v-if="(status === 'listening' || status === 'completed') && recentOutputs.length">
        <div class="recent-label">最近识别</div>
        <div v-for="(item, i) in recentOutputs" :key="i" class="recent-line" :class="{ triggered: item.keyword }">
          <span class="recent-ts">{{ item.ts }}</span>
          <span class="recent-text">{{ item.text }}</span>
          <span v-if="item.keyword" class="recent-kw">★{{ item.keyword }}</span>
        </div>
      </div>

      <!-- Stats -->
      <div class="stats-row" v-if="status === 'listening' || status === 'completed'">
        <span>累积 {{ data?.history_count || 0 }} 条</span>
        <span class="stats-sep">|</span>
        <span>触发 {{ data?.trigger_count || 0 }} 次</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待音频流...</div>
      <div v-if="status === 'error'" class="error-text">{{ summary || 'STT 错误' }}</div>
    </template>

    <!-- Edit Mode: config tab -->
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
    <template v-if="activeTab === 'fulltext'">
      <div class="fulltext-panel">
        <div v-if="!fulltextLines.length" class="hint-text">暂无全文数据</div>
        <div v-else class="fulltext-lines">
          <div v-for="(line, i) in fulltextLines" :key="i" class="ft-line" :class="{ triggered: line.keyword }">
            <span class="ft-ts">{{ line.ts }}</span>
            <span class="ft-text">{{ line.text }}</span>
            <span v-if="line.keyword" class="ft-kw">★ {{ line.keyword }}</span>
          </div>
        </div>
      </div>
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
  const map = { pending: '等待中', listening: '监听中', processing: '识别中', completed: '已触发', error: '错误' }
  return map[props.status] || props.status
})

const configFields = [
  { key: 'engine', label: '识别引擎', type: 'chip-toggle', options: [
    { value: 'sensevoice', label: 'SenseVoice' }, { value: 'whisper', label: 'Whisper' }, { value: 'minimax', label: 'MiniMax' }
  ]},
  { key: 'keywords', label: '关键词列表', type: 'tags', placeholder: '+ 添加关键词' },
  { key: 'sample_rate', label: '采样率 (Hz)', type: 'number', min: 8000, max: 48000, placeholder: '16000' }
]

// Show last 3 outputs from logs
const recentOutputs = computed(() => {
  return (props.logs || [])
    .filter(l => l.level === 'info' && l.message?.startsWith('识别:'))
    .slice(-3)
    .map(l => {
      const match = l.message?.match(/识别:\s*"(.+?)"/)
      const kwMatch = l.message?.match(/关键词:\s*"(.+?)"/)
      return { ts: l.timestamp, text: match?.[1] || l.message, keyword: kwMatch?.[1] || null }
    })
    .reverse()
})

const fulltextLines = computed(() => {
  return (props.logs || [])
    .filter(l => l.level === 'info' && l.message?.startsWith('识别:'))
    .map(l => {
      const match = l.message?.match(/识别:\s*"(.+?)"/)
      const kwMatch = l.message?.match(/关键词:\s*"(.+?)"/)
      return { ts: l.timestamp, text: match?.[1] || l.message, keyword: kwMatch?.[1] || null }
    })
})

const ioInputs = computed(() => ({
  'stt-in': 'AudioBus（内部音频总线）'
}))
const ioOutputs = computed(() => ({
  'text-out': props.data?.text || '(等待识别)',
  'meta-keyword': props.data?.trigger_keyword || '(未触发)',
  'meta-confidence': props.data?.confidence != null ? String(props.data.confidence) : '(无数据)',
  'meta-history-count': props.data?.history_count != null ? String(props.data.history_count) : '0'
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
.stt-listen-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.listening { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.processing { background: #4a8eff; animation: pulse 0.8s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.keyword-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #ef6719; box-shadow: 0 0 8px rgba(239,103,25,0.6);
  animation: keywordPulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
@keyframes keywordPulse { 0%,100% { opacity: 0.4; transform: scale(1); } 50% { opacity: 1; transform: scale(1.3); } }

.config-chips { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 6px; }
.config-chip {
  padding: 1px 6px; border-radius: 9999px;
  font-size: 8px; font-family: 'Space Grotesk', sans-serif; font-weight: 500;
  background: rgba(255,182,149,0.1); border: 1px solid rgba(239,103,25,0.3); color: #ffb695;
}
.config-chip.engine {
  background: rgba(173,199,255,0.1); border-color: rgba(173,199,255,0.3); color: #adc7ff;
}

.recog-preview { display: flex; align-items: center; gap: 4px; margin-bottom: 6px; flex-wrap: wrap; }
.recog-icon { font-size: 14px; color: #4a8eff; }
.recog-text { font-size: 10px; color: #e0e2ed; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-bar { width: 100%; height: 2px; background: #31353d; border-radius: 1px; overflow: hidden; }
.mini-bar-fill { height: 100%; background: #4a8eff; border-radius: 1px; transition: width 0.3s; }

.recent-outputs { margin-bottom: 4px; }
.recent-label { font-size: 8px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
.recent-line { display: flex; align-items: baseline; gap: 4px; padding: 1px 0; font-size: 9px; }
.recent-line.triggered { background: rgba(239,103,25,0.08); border-radius: 2px; }
.recent-ts { color: #64748b; font-family: 'Space Grotesk', sans-serif; flex-shrink: 0; }
.recent-text { color: #c1c6d7; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent-kw { color: #ef6719; font-weight: 600; flex-shrink: 0; }

.stats-row { display: flex; gap: 4px; font-size: 9px; color: #8b90a0; }
.stats-sep { color: #414754; }

.fulltext-panel { max-height: 200px; overflow-y: auto; }
.fulltext-lines { display: flex; flex-direction: column; gap: 2px; }
.ft-line { display: flex; align-items: baseline; gap: 4px; font-size: 9px; padding: 1px 2px; }
.ft-line.triggered { background: rgba(239,103,25,0.1); border-radius: 2px; }
.ft-ts { color: #64748b; font-family: 'Space Grotesk', sans-serif; flex-shrink: 0; }
.ft-text { color: #c1c6d7; }
.ft-kw { color: #ef6719; font-weight: 600; flex-shrink: 0; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
