<template>
  <div class="port-popover-overlay" @click.stop="$emit('close')" />
  <div class="port-popover" :style="popStyle">
    <div class="pp-head">
      <span class="pp-dot" :class="portDef?.data_type === 'event' ? 'dot-event' : 'dot-data'" />
      <span class="pp-title">{{ portDef?.label || portId }}</span>
      <span class="pp-type">{{ portDef?.data_type || '' }}</span>
      <button class="pp-close" @click.stop="$emit('close')">&times;</button>
    </div>

    <div class="pp-body">
      <!-- Connected info -->
      <div v-if="connection" class="pp-section">
        <div class="pp-label">连线状态</div>
        <div class="pp-connected">
          <span v-if="side === 'input'">← {{ connection.from_node }}.{{ connection.from_port }}</span>
          <span v-else>→ {{ connection.to_node }}.{{ connection.to_port }}</span>
        </div>
        <button v-if="editMode" class="pp-disconnect" @click="disconnect">断开连线</button>
      </div>

      <!-- Data source (input ports only, in edit mode, NOT event type) -->
      <div v-if="side === 'input' && portDef?.data_type !== 'event' && editMode" class="pp-section">
        <div class="pp-label">数据来源</div>
        <div class="pp-source-opts">
          <label class="pp-radio" v-for="opt in sourceOptions" :key="opt.value"
            :class="{ disabled: !!connection }">
            <input
              type="radio"
              :name="'source_' + nodeId + '_' + portId"
              :value="opt.value"
              v-model="sourceType"
              :disabled="!!connection"
            />
            <span>{{ opt.label }}</span>
          </label>
        </div>

        <!-- Fixed value input -->
        <div v-if="sourceType === 'fixed' && !connection" class="pp-source-input">
          <input
            type="text"
            class="pp-text-input"
            v-model="fixedValue"
            placeholder="输入固定值..."
            @blur="saveFixedValue"
            @keyup.enter="saveFixedValue"
          />
        </div>

        <!-- Flow parameter input -->
        <div v-if="sourceType === 'param' && !connection" class="pp-source-input">
          <input
            type="text"
            class="pp-text-input"
            v-model="paramName"
            placeholder="$param.变量名"
            @blur="saveParamRef"
            @keyup.enter="saveParamRef"
          />
          <div class="pp-hint">引用流程参数，如 $param.game_mode</div>
        </div>

        <div class="pp-hint" v-if="connection">已连线时来源锁定为连线数据</div>
      </div>

      <!-- Runtime value -->
      <div v-if="runtimeValue != null" class="pp-section">
        <div class="pp-label">当前值</div>
        <div class="pp-value">{{ runtimeValue }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  nodeId: { type: String, required: true },
  portId: { type: String, required: true },
  side: { type: String, required: true },
  editMode: { type: Boolean, default: false },
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
})

const emit = defineEmits(['close'])

const editorStore = useEditorStore()
const executionStore = useExecutionStore()

const sourceType = ref('connection')
const fixedValue = ref('')
const paramName = ref('')

const sourceOptions = [
  { value: 'connection', label: '连线数据' },
  { value: 'fixed', label: '固定值' },
  { value: 'param', label: '流程参数' },
]

const node = computed(() => editorStore.nodes.find((n) => n.id === props.nodeId))
const nodeTypeDef = computed(() => editorStore.getNodeTypeDef(node.value?.type))
const portDef = computed(() => {
  const ports = props.side === 'input'
    ? nodeTypeDef.value?.ports?.inputs
    : nodeTypeDef.value?.ports?.outputs
  return ports?.find((p) => p.id === props.portId) || null
})

const connection = computed(() => {
  if (props.side === 'input') {
    return editorStore.connections.find((c) =>
      c.to_node === props.nodeId && c.to_port === props.portId) || null
  }
  return editorStore.connections.find((c) =>
    c.from_node === props.nodeId && c.from_port === props.portId) || null
})

const runtimeValue = computed(() => {
  const state = executionStore.getNodeStatus(props.nodeId)
  return state?.data?.[props.portId] || null
})

const popStyle = computed(() => ({
  left: Math.min(props.x, window.innerWidth - 260) + 'px',
  top: Math.min(props.y, window.innerHeight - 360) + 'px',
}))

// Init source type from existing config
watch(() => [props.nodeId, props.portId, connection.value], () => {
  if (connection.value) {
    sourceType.value = 'connection'
    return
  }
  const cfg = node.value?.config
  const portSources = cfg?._port_sources || {}
  const ps = portSources[props.portId]
  if (ps) {
    sourceType.value = ps.type || 'connection'
    if (ps.type === 'fixed') fixedValue.value = ps.value || ''
    if (ps.type === 'param') paramName.value = ps.value || ''
  } else {
    sourceType.value = 'connection'
  }
}, { immediate: true })

function saveFixedValue() {
  if (!node.value) return
  const portSources = { ...(node.value.config?._port_sources || {}) }
  portSources[props.portId] = { type: 'fixed', value: fixedValue.value }
  editorStore.updateConfigImmediate(props.nodeId, { _port_sources: portSources })
}

function saveParamRef() {
  if (!node.value) return
  const portSources = { ...(node.value.config?._port_sources || {}) }
  portSources[props.portId] = { type: 'param', value: paramName.value }
  editorStore.updateConfigImmediate(props.nodeId, { _port_sources: portSources })
}

function disconnect() {
  if (connection.value) {
    editorStore.deleteConnection(connection.value.id)
  }
}
</script>

<style scoped>
.port-popover-overlay { position: fixed; inset: 0; z-index: 149; }
.port-popover {
  position: fixed; z-index: 150; width: 250px;
  background: #181c23; border: 1px solid #414754;
  border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  overflow: hidden;
}
.pp-head {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 12px; border-bottom: 1px solid rgba(65,71,84,0.4);
}
.pp-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.dot-data { background: #4edea3; }
.dot-event { background: #ffb695; }
.pp-title { flex: 1; font-size: 12px; font-weight: 600; color: #e0e2ed; }
.pp-type {
  font-size: 8px; color: #64748b; font-family: 'Space Grotesk', sans-serif;
  background: rgba(100,116,139,0.1); padding: 1px 5px; border-radius: 9999px;
}
.pp-close { background: none; border: none; color: #8b90a0; font-size: 16px; cursor: pointer; }
.pp-close:hover { color: #e0e2ed; }

.pp-body { padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; max-height: 320px; overflow-y: auto; }
.pp-section { }
.pp-label {
  font-size: 9px; color: #64748b; text-transform: uppercase;
  letter-spacing: 0.06em; font-family: 'Space Grotesk', sans-serif;
  margin-bottom: 4px;
}
.pp-connected { font-size: 10px; color: #4edea3; font-family: 'Space Grotesk', sans-serif; }
.pp-disconnect {
  margin-top: 4px; padding: 3px 8px; border-radius: 4px;
  border: 1px solid #414754; background: transparent; color: #ffb4ab;
  font-size: 9px; cursor: pointer; transition: all 0.15s;
}
.pp-disconnect:hover { border-color: #ffb4ab; background: rgba(255,180,171,0.06); }

.pp-source-opts { display: flex; flex-direction: column; gap: 3px; }
.pp-radio {
  display: flex; align-items: center; gap: 5px;
  font-size: 10px; color: #c1c6d7; cursor: pointer; padding: 2px 0;
}
.pp-radio.disabled { opacity: 0.4; cursor: not-allowed; }
.pp-radio input[type="radio"] { accent-color: #adc7ff; margin: 0; }
.pp-source-input { margin-top: 6px; }
.pp-text-input {
  width: 100%; height: 30px; padding: 0 8px;
  border-radius: 4px; border: 1px solid #414754;
  background: #10131b; color: #e0e2ed;
  font-size: 11px; font-family: 'Inter', sans-serif; outline: none;
  transition: border-color 0.15s; box-sizing: border-box;
}
.pp-text-input:focus { border-color: #adc7ff; }
.pp-hint { font-size: 8px; color: #64748b; margin-top: 3px; }
.pp-value {
  font-size: 10px; color: #e0e2ed; padding: 4px 6px;
  background: rgba(11,14,22,0.6); border-radius: 3px;
  word-break: break-all; max-height: 60px; overflow-y: auto;
}
</style>
