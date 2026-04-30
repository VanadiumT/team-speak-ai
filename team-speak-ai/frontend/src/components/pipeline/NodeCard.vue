<template>
  <div
    class="node-card"
    :class="[borderClass, { 'node-pulse': isProcessing, 'selected': isSelected }]"
    :style="{ left: node.position?.x + 'px', top: node.position?.y + 'px', width: nodeWidth + 'px' }"
    @mousedown="onDragStart"
    @click.stop="onClick"
    @dblclick.stop="onDoubleClick"
    @contextmenu.prevent="onContextMenu"
  >
    <!-- Workflow badge -->
    <div v-if="stepNumber" class="workflow-badge" :style="{ borderColor: badgeColor, color: badgeColor }">
      {{ stepNumber }}
    </div>

    <!-- I/O Ports -->
    <IOPort
      v-for="port in inputPorts"
      :key="port.id"
      side="left"
      :position="port.position?.top || defaultPortTop(port.id, 'input')"
      :label="port.label"
      :port-state="getPortState(port.id)"
      :data-type="port.data_type"
      :data-node-id="node.id"
      :data-port-id="port.id"
      :edit-mode="editMode"
      @port-drag-start="(e) => $emit('portDragStart', { nodeId: node.id, portId: port.id, event: e })"
      @port-click="(e) => $emit('portClick', { nodeId: node.id, portId: port.id, event: e })"
    />
    <IOPort
      v-for="port in outputPorts"
      :key="port.id"
      side="right"
      :position="port.position?.top || defaultPortTop(port.id, 'output')"
      :label="port.label"
      :port-state="getPortState(port.id)"
      :data-type="port.data_type"
      :data-node-id="node.id"
      :data-port-id="port.id"
      :edit-mode="editMode"
      @port-drag-start="(e) => $emit('portDragStart', { nodeId: node.id, portId: port.id, event: e })"
      @port-click="(e) => $emit('portClick', { nodeId: node.id, portId: port.id, event: e })"
    />

    <!-- Header -->
    <div class="node-header">
      <span class="material-symbols-outlined node-icon" :style="{ color: iconColor }">{{ nodeIcon }}</span>
      <span class="node-title">{{ node.name || nodeTypeDef?.name || node.type }}</span>
      <span class="node-status-badge" :class="statusClass">{{ statusLabel }}</span>
      <div v-if="isListening" class="keyword-dot"></div>
    </div>

    <!-- Tab bar -->
    <div v-if="tabs.length > 0" class="node-tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click.stop="activeTab = tab.id"
      >{{ tab.label }}</button>
    </div>

    <!-- Body -->
    <div class="node-body">
      <slot :tab="activeTab" :status="nodeStatus">
        <div class="node-default-body">
          <div class="node-status-row">
            <span class="node-status-label">状态</span>
            <span :class="statusClass" class="node-status-value">
              <span class="status-dot" :class="statusClass"></span>
              {{ statusLabel }}
            </span>
          </div>
          <div v-if="nodeStatus === 'processing'" class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
        </div>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import IOPort from './IOPort.vue'
import { useEditorStore } from '@/stores/editor.js'
import { useExecutionStore } from '@/stores/execution.js'

const props = defineProps({
  node: { type: Object, required: true },
  stepNumber: { type: [String, Number], default: '' },
  editMode: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'dragstart', 'dragend', 'portDragStart', 'portClick'])

const editorStore = useEditorStore()
const executionStore = useExecutionStore()
const activeTab = ref('config')

const isSelected = ref(false)

// ── Node type metadata ──
const nodeTypeDef = computed(() => {
  return editorStore.nodeTypes.find((t) => t.type === props.node.type)
})

const tabs = computed(() => nodeTypeDef.value?.tabs || [])
const nodeIcon = computed(() => nodeTypeDef.value?.icon || 'smart_toy')
const iconColor = computed(() => {
  const colors = { primary: '#adc7ff', secondary: '#4edea3', tertiary: '#ffb695', outline: '#8b90a0' }
  return colors[nodeTypeDef.value?.color] || '#8b90a0'
})

// ── Ports ──
const inputPorts = computed(() => nodeTypeDef.value?.ports?.inputs || [])
const outputPorts = computed(() => nodeTypeDef.value?.ports?.outputs || [])

// 端口 top 值参考原型 pipeline-prototype_flow.html
function defaultPortTop(portId, side) {
  // 每个节点类型的端口位置固定，与原型一致
  const nodeType = props.node.type
  if (side === 'input') {
    if (nodeType === 'context_build') {
      const idx = inputPorts.value.findIndex((p) => p.id === portId)
      return [30, 58, 86, 114][idx] || 30
    }
    return 30
  }
  // output side
  if (nodeType === 'input_image') {
    const idx = outputPorts.value.findIndex((p) => p.id === portId)
    return [30, 72][idx] || 30
  }
  if (nodeType === 'stt_history') {
    const idx = outputPorts.value.findIndex((p) => p.id === portId)
    return [72, 110][idx] || 55
  }
  if (nodeType === 'ts_output') return 72
  return 55
}

function getPortState(portId) {
  const conns = editorStore.connections
  const hasConn = conns.some((c) =>
    (c.from_node === props.node.id && c.from_port === portId) ||
    (c.to_node === props.node.id && c.to_port === portId)
  )
  if (!hasConn) return 'disconnected'
  const ns = executionStore.getNodeStatus(props.node.id)
  if (ns.status === 'processing') return 'flowing'
  return 'connected'
}

// ── Status ──
const nodeStatus = computed(() => {
  return executionStore.getNodeStatus(props.node.id).status || 'pending'
})

const isProcessing = computed(() => nodeStatus.value === 'processing')
const isListening = computed(() => nodeStatus.value === 'listening')

const progressPercent = computed(() => {
  const p = executionStore.getNodeStatus(props.node.id).progress
  return p ? Math.round(p * 100) : 0
})

const statusClass = computed(() => {
  const map = {
    pending: 'status-pending', processing: 'status-processing',
    completed: 'status-completed', error: 'status-error',
    listening: 'status-listening',
  }
  return map[nodeStatus.value] || 'status-pending'
})

const statusLabel = computed(() => {
  const map = { pending: '待命', processing: '处理中', completed: '已完成', error: '错误', listening: '监听中' }
  return map[nodeStatus.value] || nodeStatus.value
})

const borderClass = computed(() => {
  const map = {
    pending: 'border-outline', processing: 'border-primary node-pulse',
    completed: 'border-secondary', error: 'border-error', listening: 'border-primary',
  }
  return map[nodeStatus.value] || 'border-outline'
})

const badgeColor = computed(() => {
  const colorMap = { primary: '#adc7ff', secondary: '#4edea3', tertiary: '#ef6719', outline: '#8b90a0' }
  return colorMap[nodeTypeDef.value?.color] || '#4edea3'
})

const nodeWidth = computed(() => {
  const widthMap = {
    input_image: 220, ocr: 220, tts: 220, ts_output: 220, ts_input: 220,
    context_build: 250, llm: 250,
    stt_history: 280, stt_listen: 320,
  }
  return widthMap[props.node.type] || 250
})

// ── Drag (直接操作 DOM，松手才同步 store，确保跟手流畅) ──
let nodeDragActive = false
let nodeDragMoved = false
const cardEl = ref(null)

function onDragStart(e) {
  if (e.button !== 0) return // 中键/右键留给画布平移
  e.stopPropagation()
  if (!props.editMode || editorStore.isReadOnly) return
  if (e.target.closest('.io-port')) return
  if (nodeDragActive) return

  nodeDragActive = true
  nodeDragMoved = false
  const el = e.currentTarget  // 直接拿 DOM 元素
  const startCanvasX = props.node.position.x
  const startCanvasY = props.node.position.y
  const startScreenX = e.clientX
  const startScreenY = e.clientY
  el.style.willChange = 'left, top'
  el.style.zIndex = '25'

  const onMove = (ev) => {
    if (!nodeDragActive) return
    const dx = ev.clientX - startScreenX
    const dy = ev.clientY - startScreenY
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
    nodeDragMoved = true
    el.style.left = (startCanvasX + dx) + 'px'
    el.style.top  = (startCanvasY + dy) + 'px'
  }

  const onUp = (ev) => {
    nodeDragActive = false
    el.style.willChange = 'auto'
    el.style.zIndex = '10'
    if (nodeDragMoved) {
      const dx = ev.clientX - startScreenX
      const dy = ev.clientY - startScreenY
      editorStore.moveNodeLocal(props.node.id, startCanvasX + dx, startCanvasY + dy)
      editorStore.commitMoveNode(props.node.id)
    }
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onClick() {
  if (!props.editMode) return
  isSelected.value = !isSelected.value
  emit('select', props.node)
}

function onDoubleClick() {
  if (!props.editMode) return
  emit('select', props.node)
}

function onContextMenu() {
  if (!props.editMode) return
}
</script>

<style scoped>
.node-card {
  position: absolute;
  background: rgba(28, 32, 39, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 8px;
  z-index: 10;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  border: 1px solid;
  user-select: none;
}

.node-card:hover { transform: translateY(-2px); z-index: 20 !important; }

.node-card.selected {
  border-color: #4a8eff !important;
  box-shadow: 0 0 16px rgba(74, 142, 255, 0.3);
}

.border-outline { border-color: rgba(65, 71, 84, 0.5); }
.border-primary { border: 2px solid rgba(173, 199, 255, 0.5); }
.border-secondary { border-color: rgba(78, 222, 163, 0.3); }
.border-error { border-color: rgba(255, 180, 171, 0.5); }

.node-pulse { animation: nodePulse 2s ease-in-out infinite; }

@keyframes nodePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(173, 199, 255, 0.4); }
  50% { box-shadow: 0 0 20px 4px rgba(173, 199, 255, 0.15); }
}

.node-header {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(65, 71, 84, 0.5);
}

.node-icon { font-size: 14px; }

.node-title {
  font-size: 13px; font-weight: 600; color: #e0e2ed; flex: 1;
}

.node-status-badge {
  font-size: 10px; font-family: 'Space Grotesk', sans-serif;
  font-weight: 500; letter-spacing: 0.05em;
}

.status-pending { color: #8b90a0; }
.status-processing { color: #adc7ff; }
.status-completed { color: #4edea3; }
.status-error { color: #ffb4ab; }
.status-listening { color: #adc7ff; }

.keyword-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #ef6719; margin-left: 4px;
  animation: keywordPulse 1.5s ease-in-out infinite;
}

@keyframes keywordPulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.3); }
}

.node-tab-bar { display: flex; border-bottom: 1px solid rgba(65, 71, 84, 0.5); }

.tab-btn {
  position: relative; padding: 6px 12px;
  font-size: 11px; font-family: 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em; font-weight: 500;
  color: #8b90a0; cursor: pointer; transition: color 0.2s;
  border: none; border-bottom: 2px solid transparent; background: transparent;
}
.tab-btn:hover { color: #c1c6d7; }
.tab-btn.active { color: #adc7ff; border-bottom-color: #adc7ff; }

.node-body { padding: 10px; }

.node-default-body { display: flex; flex-direction: column; gap: 8px; }

.node-status-row {
  display: flex; justify-content: space-between; align-items: center; font-size: 12px;
}

.node-status-label { color: #8b90a0; }

.node-status-value { display: flex; align-items: center; gap: 4px; }

.status-dot {
  width: 6px; height: 6px; border-radius: 50%;
}

.status-pending .status-dot { background: #8b90a0; }
.status-processing .status-dot {
  background: #adc7ff;
  box-shadow: 0 0 8px rgba(173, 199, 255, 0.6);
  animation: pulse 1.5s infinite;
}
.status-completed .status-dot {
  background: #4edea3;
  box-shadow: 0 0 8px rgba(78, 222, 163, 0.6);
}
.status-error .status-dot {
  background: #ffb4ab;
  box-shadow: 0 0 8px rgba(255, 180, 171, 0.6);
}
.status-listening .status-dot {
  background: #adc7ff;
  box-shadow: 0 0 8px rgba(173, 199, 255, 0.6);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.progress-bar {
  width: 100%; background: #31353d; border-radius: 9999px; height: 4px;
}
.progress-fill {
  background: #adc7ff; height: 4px; border-radius: 9999px; transition: width 0.3s;
}

.workflow-badge {
  position: absolute; top: -10px; right: -10px;
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: bold;
  font-family: 'Space Grotesk', sans-serif;
  z-index: 40; background: #10131b; border: 2px solid;
}
</style>
