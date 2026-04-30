<template>
  <div
    class="pipeline-canvas"
    ref="canvasRef"
    :class="{ 'is-panning': isPanning }"
    @wheel.prevent="onWheel"
    @mousedown="onPanStart"
  >
    <!-- Grid background -->
    <div class="canvas-grid" :style="gridStyle"></div>

    <!-- Main content (zoomable) -->
    <div
      id="canvas-content"
      class="canvas-content flow-view"
      :data-flow="activeFlowView"
      :style="contentStyle"
    >
      <!-- SVG connections -->
      <svg
        class="connections-svg"
        ref="svgRef"
        :width="canvasWidth"
        :height="canvasHeight"
      >
        <defs>
          <marker id="arrowEvent" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <polygon points="0,2 10,5 0,8" fill="#adc7ff" opacity="0.6" />
          </marker>
          <marker id="arrowData" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <polygon points="0,2 10,5 0,8" fill="#4edea3" opacity="0.8" />
          </marker>
          <marker id="arrowDataFlow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <polygon points="0,2 10,5 0,8" fill="#4a8eff" opacity="0.8" />
          </marker>
        </defs>

        <!-- Connection lines -->
        <g v-for="conn in connectionPaths" :key="conn.id" :class="conn.groupClass" class="conn-hit-area" @click="onConnectionClick(conn)">
          <path
            :d="conn.path"
            fill="none"
            :stroke="conn.stroke"
            :stroke-width="conn.selected ? 4 : conn.width"
            :stroke-dasharray="conn.dash"
            :class="conn.lineClass"
            :marker-end="conn.marker"
            :opacity="conn.opacity"
            style="cursor:pointer"
          />
          <rect
            v-if="conn.label"
            :x="conn.labelX - conn.labelW / 2 - 6"
            :y="conn.labelY - 9"
            :width="conn.labelW + 12"
            height="17"
            rx="3"
            fill="rgba(11, 14, 22, 0.92)"
          />
          <text
            v-if="conn.label"
            :x="conn.labelX"
            :y="conn.labelY + 3"
            text-anchor="middle"
            :fill="conn.stroke"
            font-size="10"
            font-family="Space Grotesk"
            font-weight="bold"
            style="pointer-events:none"
          >{{ conn.label }}</text>
        </g>

        <!-- Temporary line while dragging -->
        <line
          v-if="dragLine.visible"
          :x1="dragLine.x1" :y1="dragLine.y1"
          :x2="dragLine.x2" :y2="dragLine.y2"
          stroke="#4a8eff" stroke-width="2.5"
          stroke-dasharray="8 4"
        />
      </svg>

      <!-- Node cards -->
      <NodeCard
        v-for="node in editorStore.nodes"
        :key="node.id"
        :node="node"
        :step-number="getStepNumber(node.id)"
        :edit-mode="editMode"
        @select="onNodeSelect"
        @port-drag-start="onPortDragStart"
        @port-click="onPortClick"
      />

      <!-- Empty hint -->
      <div v-if="editorStore.nodes.length === 0" class="empty-hint">
        <span class="material-symbols-outlined">dashboard_customize</span>
        <p>从左侧<span class="hl">工具面板</span>拖拽节点到画布</p>
      </div>
    </div>

    <!-- Zoom controls -->
    <CanvasControls
      :zoom="currentZoom"
      :activeView="activeFlowView"
      @update:active-view="activeFlowView = $event"
      @zoom="zoomBy"
      @reset-zoom="resetZoom"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import NodeCard from './NodeCard.vue'
import CanvasControls from './CanvasControls.vue'
import { useEditorStore } from '@/stores/editor.js'
import { useExecutionStore } from '@/stores/execution.js'

const props = defineProps({
  editMode: { type: Boolean, default: false },
})

const editorStore = useEditorStore()
const executionStore = useExecutionStore()

const canvasRef = ref(null)
const svgRef = ref(null)
const currentZoom = ref(1.0)
const activeFlowView = ref('all')
const isPanning = ref(false)
const selectedConnId = ref(null)

const ZOOM_MIN = 0.25
const ZOOM_MAX = 3.0

const canvasWidth = computed(() => editorStore.canvasSize.width)
const canvasHeight = computed(() => editorStore.canvasSize.height)

// ── Zoom ──
const contentStyle = computed(() => ({
  transform: `scale(${currentZoom.value})`,
  transformOrigin: '0 0',
  width: canvasWidth.value + 'px',
  height: canvasHeight.value + 'px',
}))

const gridStyle = computed(() => ({
  width: (canvasWidth.value * currentZoom.value) + 'px',
  height: (canvasHeight.value * currentZoom.value) + 'px',
  backgroundSize: (32 * currentZoom.value) + 'px ' + (32 * currentZoom.value) + 'px',
}))

function zoomBy(delta) {
  currentZoom.value = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, currentZoom.value + delta))
}

function resetZoom() {
  currentZoom.value = 1.0
  if (canvasRef.value) {
    canvasRef.value.scrollLeft = 0
    canvasRef.value.scrollTop = 0
  }
}

function onWheel(e) {
  const delta = e.deltaY > 0 ? -0.05 : 0.05
  zoomBy(delta)
}

// ── Pan (middle mouse button) ──
let panStart = { x: 0, y: 0, scrollX: 0, scrollY: 0 }

function onPanStart(e) {
  if (e.button !== 1) return
  e.preventDefault()
  isPanning.value = true
  panStart = {
    x: e.clientX, y: e.clientY,
    scrollX: canvasRef.value.scrollLeft,
    scrollY: canvasRef.value.scrollTop,
  }
}

function onPanMove(e) {
  if (!isPanning.value) return
  canvasRef.value.scrollLeft = panStart.scrollX - (e.clientX - panStart.x)
  canvasRef.value.scrollTop = panStart.scrollY - (e.clientY - panStart.y)
}

function onPanEnd() {
  isPanning.value = false
}

onMounted(() => {
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanEnd)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
})

// ── Connection lines ──
const connectionPaths = computed(() => {
  return editorStore.connections.map((conn) => {
    const fromNode = editorStore.nodes.find((n) => n.id === conn.from_node)
    const toNode = editorStore.nodes.find((n) => n.id === conn.to_node)
    if (!fromNode || !toNode) return null

    const fromPos = getPortPosition(fromNode, conn.from_port, 'output')
    const toPos = getPortPosition(toNode, conn.to_port, 'input')
    if (!fromPos || !toPos) return null

    const fromX = fromPos.x
    const fromY = fromPos.y
    const toX = toPos.x
    const toY = toPos.y

    const fromStatus = executionStore.getNodeStatus(conn.from_node).status
    const isActive = fromStatus === 'processing'

    let stroke, width, dash, marker, lineClass, opacity, groupClass
    if (conn.type === 'event') {
      stroke = '#adc7ff'; width = 2.5; dash = 'none'
      marker = 'url(#arrowEvent)'; lineClass = ''; opacity = 1
      groupClass = 'event-only'
    } else if (isActive) {
      stroke = '#4a8eff'; width = 2.5; dash = 'none'
      marker = 'url(#arrowDataFlow)'; lineClass = 'flow-line'; opacity = 1
      groupClass = 'data-only'
    } else {
      stroke = '#4edea3'; width = 2.5; dash = '10 5'
      marker = 'url(#arrowData)'; lineClass = 'flow-line'; opacity = 1
      groupClass = 'data-only'
    }

    const yDiff = Math.abs(fromY - toY)
    let path
    if (yDiff < 80) {
      const midX = (fromX + toX) / 2
      path = `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`
    } else {
      const cpOffset = Math.abs(fromX - toX) * 0.5
      path = `M ${fromX} ${fromY} C ${fromX + cpOffset} ${fromY}, ${toX - cpOffset} ${toY}, ${toX} ${toY}`
    }

    const labelX = (fromX + toX) / 2
    const labelY = (fromY + toY) / 2
    const label = getPortLabel(fromNode, conn.from_port)

    return {
      id: conn.id, path,
      stroke, width, dash, marker, lineClass, opacity, groupClass,
      label, labelX, labelY,
      labelW: label ? label.length * 7 : 0,
      selected: selectedConnId.value === conn.id,
    }
  }).filter(Boolean)
})

function onConnectionClick(conn) {
  if (!props.editMode) return
  if (selectedConnId.value === conn.id) {
    selectedConnId.value = null
  } else {
    selectedConnId.value = conn.id
  }
}

// ── Port-to-port connection drag ──
const dragLine = ref({ visible: false, x1: 0, y1: 0, x2: 0, y2: 0 })

function onPortDragStart({ nodeId, portId, event }) {
  if (!props.editMode) return
  const portEl = event.target.closest('.io-port')
  if (!portEl || portEl.classList.contains('input-port')) return

  const rect = portEl.getBoundingClientRect()
  const x1 = rect.left + 7
  const y1 = rect.top + 7
  dragLine.value = { visible: true, x1, y1, x2: event.clientX, y2: event.clientY }

  const fromNode = nodeId
  const fromPort = portId

  function onMove(ev) {
    dragLine.value = { ...dragLine.value, x2: ev.clientX, y2: ev.clientY }
    // Highlight compatible ports
    document.querySelectorAll('.io-port.input-port').forEach((el) => {
      const r = el.getBoundingClientRect()
      const over = ev.clientX > r.left - 6 && ev.clientX < r.right + 6 &&
                    ev.clientY > r.top - 6 && ev.clientY < r.bottom + 6
      el.classList.remove('drag-over', 'valid', 'invalid')
      if (over) {
        el.classList.add('drag-over')
        const toNode = el.dataset.nodeId
        const toPort = el.dataset.portId
        const valid = editorStore.arePortsCompatible(fromNode, fromPort, toNode, toPort)
        el.classList.add(valid ? 'valid' : 'invalid')
      }
    })
  }

  function onUp(ev) {
    dragLine.value.visible = false
    document.querySelectorAll('.io-port').forEach((el) => el.classList.remove('drag-over', 'valid', 'invalid'))
    // Check target
    const target = document.elementFromPoint(ev.clientX, ev.clientY)
    const portEl = target?.closest('.io-port.input-port')
    if (portEl) {
      const toNode = portEl.dataset.nodeId
      const toPort = portEl.dataset.portId
      if (toNode && toPort && editorStore.arePortsCompatible(fromNode, fromPort, toNode, toPort)) {
        const fromPortDef = getPortDef(fromNode, fromPort, 'output')
        const type = fromPortDef?.data_type === 'event' ? 'event' : 'data'
        editorStore.createConnection(fromNode, fromPort, toNode, toPort, type)
      }
    }
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

// ── Port click ──
function onPortClick({ nodeId, portId, event }) {
  if (!props.editMode) return
  // Deselect connection
  selectedConnId.value = null
}

function getPortDef(nodeId, portId, side) {
  const node = editorStore.nodes.find((n) => n.id === nodeId)
  if (!node) return null
  return editorStore.getPortDef(node, portId, side)
}

// ── Helpers ──
function getPortPosition(node, portId, side) {
  const typeDef = editorStore.getNodeTypeDef(node.type)
  if (!typeDef) return null
  const ports = side === 'input' ? typeDef.ports?.inputs : typeDef.ports?.outputs
  const port = ports?.find((p) => p.id === portId)
  if (!port) {
    return {
      x: side === 'input' ? node.position.x : node.position.x + getNodeWidth(node),
      y: node.position.y + 30,
    }
  }
  const nodeW = getNodeWidth(node)
  return {
    x: side === 'input' ? node.position.x : node.position.x + nodeW,
    y: node.position.y + port.position.top + 7,
  }
}

function getPortLabel(node, portId) {
  const typeDef = editorStore.getNodeTypeDef(node.type)
  if (!typeDef) return ''
  const port = typeDef.ports?.outputs?.find((p) => p.id === portId)
  return port?.label || ''
}

function getNodeWidth(node) {
  const widthMap = {
    input_image: 220, ocr: 220, tts: 220, ts_output: 220, ts_input: 220,
    context_build: 250, llm: 250,
    stt_history: 280,
    stt_listen: 320,
  }
  return widthMap[node.type] || 250
}

function getStepNumber(nodeId) {
  const idx = editorStore.nodes.findIndex((n) => n.id === nodeId)
  return idx >= 0 ? String.fromCharCode(0x2460 + idx) : ''
}

// ── Keyboard ──
function onKeydown(e) {
  if (!props.editMode) return
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (selectedConnId.value) {
      e.preventDefault()
      editorStore.deleteConnection(selectedConnId.value)
      selectedConnId.value = null
    }
  }
  if (e.key === 'Escape') {
    selectedConnId.value = null
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})

// ── Zoom storage for palette ──
// Expose current zoom as a global for NodePalette coordinate conversion
const emit = defineEmits(['select-node'])

function onNodeSelect(node) {
  emit('select-node', node.id)
}
</script>

<style scoped>
.pipeline-canvas {
  flex: 1;
  margin-left: 256px;
  position: relative;
  background: #121417;
  overflow: auto;
  height: calc(100vh - 88px);
}

.pipeline-canvas.is-panning {
  cursor: grabbing;
  user-select: none;
}

.canvas-grid {
  position: absolute;
  top: 0; left: 0; z-index: 0;
  pointer-events: none; opacity: 0.15;
  background-image:
    linear-gradient(#31353d 1px, transparent 1px),
    linear-gradient(90deg, #31353d 1px, transparent 1px);
}

.canvas-content {
  position: relative;
  z-index: 10;
  padding: 32px;
  transition: transform 0.2s ease;
}

.flow-view[data-flow="data"] .event-only { display: none !important; }
.flow-view[data-flow="event"] .data-only { display: none !important; }

.connections-svg {
  position: absolute;
  top: 0; left: 0;
  pointer-events: none;
  z-index: 0;
}

.flow-line {
  animation: flowDash 1.0s linear infinite;
}

@keyframes flowDash {
  to { stroke-dashoffset: -24; }
}

.empty-hint {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  pointer-events: none; z-index: 20;
  color: rgba(139, 144, 160, 0.4); font-size: 13px; gap: 8px;
}
.empty-hint .material-symbols-outlined { font-size: 48px; opacity: 0.3; }
.empty-hint .hl { color: rgba(173, 199, 255, 0.5); }

.pipeline-canvas::-webkit-scrollbar { width: 6px; height: 6px; }
.pipeline-canvas::-webkit-scrollbar-track { background: #10131b; }
.pipeline-canvas::-webkit-scrollbar-thumb { background: #31353d; border-radius: 3px; }
.pipeline-canvas::-webkit-scrollbar-thumb:hover { background: #414754; }
</style>
