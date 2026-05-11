<template>
  <div class="text-input-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <!-- PENDING (interactive: show input area ready) -->
      <div v-if="status === 'pending' && config?.mode === 'interactive'" class="ti-input-zone">
        <span class="material-symbols-outlined ti-icon" style="color:#64748b;">edit_note</span>
        <span class="ti-label">交互输入模式</span>
        <textarea
          class="ti-textarea"
          v-model="inputText"
          placeholder="流程到达后将在此输入文本..."
          rows="3"
          @keydown.enter.exact.prevent="submitText"
        />
        <button class="ti-submit" @click.stop="submitText" :disabled="!inputText.trim()">确认提交</button>
        <span class="ti-hint">Shift+Enter 换行，Enter 提交</span>
      </div>

      <!-- PENDING (static) -->
      <div v-else-if="status === 'pending'" class="ti-preview">
        <span class="material-symbols-outlined" style="font-size:14px;color:#64748b;">edit_note</span>
        <div class="ti-content" v-if="config?.text">{{ config.text }}</div>
        <div v-else style="font-size:10px;color:#64748b;">（未配置文本）</div>
      </div>

      <!-- WAITING for input (interactive mode) -->
      <div v-else-if="status === 'processing' && config?.mode === 'interactive' && !data?.text" class="ti-input-zone">
        <span class="material-symbols-outlined ti-icon" style="color:#ffb695;">hourglass_top</span>
        <span class="ti-label">等待输入...</span>
        <textarea
          class="ti-textarea"
          v-model="inputText"
          placeholder="在此输入文本，按回车提交..."
          rows="3"
          @keydown.enter.exact.prevent="submitText"
        />
        <button class="ti-submit" @click.stop="submitText" :disabled="!inputText.trim()">确认提交</button>
        <span class="ti-hint">Shift+Enter 换行，Enter 提交</span>
      </div>

      <!-- PROCESSING -->
      <div v-else-if="status === 'processing'" class="ti-waiting" style="color:#adc7ff;">
        <span class="material-symbols-outlined spin" style="font-size: 14px;">progress_activity</span>
        <span>处理中...</span>
      </div>

      <!-- COMPLETED -->
      <div v-else-if="status === 'completed'" class="ti-preview">
        <span class="material-symbols-outlined ti-done">check_circle</span>
        <div class="ti-content">{{ displayText || '(空)' }}</div>
      </div>

      <!-- ERROR -->
      <div v-else-if="status === 'error'" class="ti-waiting" style="color:#ffb4ab;">
        <span class="material-symbols-outlined">error</span>
        <span>错误</span>
      </div>

      <!-- fallback -->
      <div v-else class="ti-waiting">
        <span class="material-symbols-outlined" style="font-size: 14px; color: #64748b;">edit_note</span>
        <span>{{ config?.mode === 'static' ? '固定文本' : '等待输入...' }}</span>
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
import { ref, computed } from 'vue'
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
const inputText = ref('')

const displayText = computed(() => {
  return props.data?.text || props.config?.text || ''
})

const configFields = [
  { key: 'mode', label: '模式', type: 'chip-toggle', options: [
    { value: 'static', label: '静态' },
    { value: 'interactive', label: '交互' },
  ]},
  { key: 'text', label: '静态文本', type: 'textarea', placeholder: '$param.key / $sys.key 变量自动解析' },
  { key: 'notify_on_reach', label: '到达时通知输入', type: 'switch' },
]

function onConfigUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

async function submitText() {
  const text = inputText.value.trim()
  if (!text) return
  const { pipelineSocket } = await import('@/api/pipeline')
  await pipelineSocket.sendCommand(editorStore.flowId, 'node.trigger', {
    node_id: props.node.id,
    payload: { text },
  })
  inputText.value = ''
}
</script>

<style scoped>
.text-input-body { padding: 4px 0; }

.ti-waiting {
  display: flex; align-items: center; gap: 6px;
  padding: 8px; font-size: 11px; color: #64748b;
}

.ti-input-zone {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 8px 4px;
}
.ti-icon { font-size: 20px; }
.ti-label { font-size: 11px; color: #c1c6d7; }
.ti-textarea {
  width: 100%; padding: 6px; border-radius: 4px; box-sizing: border-box;
  border: 1px solid #31353d; background: #1a1e2e;
  color: #e0e2ed; font-size: 10px; font-family: 'Space Grotesk', monospace;
  outline: none; resize: vertical; line-height: 1.5;
}
.ti-textarea:focus { border-color: #adc7ff; }
.ti-submit {
  padding: 4px 14px; border-radius: 4px;
  border: 1px solid #4edea3; background: transparent; color: #4edea3;
  font-size: 10px; cursor: pointer; font-family: 'Space Grotesk', sans-serif;
}
.ti-submit:hover { background: rgba(78, 222, 163, 0.1); }
.ti-submit:disabled { opacity: 0.3; cursor: default; }
.ti-hint { font-size: 8px; color: #414754; }

.ti-preview {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 6px 8px;
}
.ti-done { font-size: 18px; color: #4edea3; }
.ti-content {
  font-size: 10px; color: #c1c6d7; white-space: pre-wrap; word-break: break-word;
  line-height: 1.5; font-family: 'Space Grotesk', monospace;
  max-height: 100px; overflow-y: auto; width: 100%;
  text-align: center;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
