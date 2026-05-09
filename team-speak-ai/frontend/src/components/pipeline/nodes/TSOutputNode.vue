<template>
  <div class="ts-output-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
      </div>

      <div v-if="status === 'processing'" class="play-info">
        <span class="material-symbols-outlined play-icon">volume_up</span>
        <span>播放中</span>
        <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
        <span class="seg-info">片段 {{ data?.segment_index ?? '-' }}/{{ data?.total_segments ?? '-' }}</span>
      </div>

      <div v-if="status === 'completed'" class="done-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>播放完成 · {{ data?.segment_count ?? 0 }} 段</span>
        <span class="loop-hint">→ 回到监听</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待音频...</div>
      <div v-if="status === 'error'" class="error-text">{{ summary || '播放失败' }}</div>
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
import NodeIODataView from './NodeIODataView.vue'
import NodeIOMgmt from './NodeIOMgmt.vue'
import NodeLogView from './NodeLogView.vue'

const editorStore = useEditorStore()

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

const statusLabel = computed(() => {
  const map = { pending: '等待音频', processing: '播放中', completed: '播放完成', error: '错误' }
  return map[props.status] || props.status
})


function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}
</script>

<style scoped>
.ts-output-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.play-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #adc7ff; flex-wrap: wrap; }
.play-icon { font-size: 16px; }
.mini-bar { flex: 1; height: 3px; background: #31353d; border-radius: 2px; overflow: hidden; min-width: 40px; }
.mini-bar-fill { height: 100%; background: #adc7ff; border-radius: 2px; transition: width 0.3s; }
.seg-info { font-size: 9px; color: #8b90a0; }

.done-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #4edea3; flex-wrap: wrap; }
.done-icon { font-size: 16px; }
.loop-hint { font-size: 9px; color: #8b90a0; }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }
</style>
