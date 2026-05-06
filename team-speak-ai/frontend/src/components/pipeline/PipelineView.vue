<template>
  <div
    ref="canvasRef"
    class="pipeline-canvas"
    :class="{ 'is-panning': isPanning, 'detail-open': props.detailPanelOpen }"
    @wheel.prevent="onWheel"
    @mousedown="onPanStart"
  >
    <div class="canvas-grid" :style="gridStyle"></div>

    <div
      id="canvas-content"
      class="canvas-content flow-view"
      :data-flow="activeFlowView"
      :style="contentStyle"
    >
      <svg
        class="connections-svg"
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
        <g v-for="conn in connectionPaths" :key="conn.id" :class="conn.groupClass" class="conn-hit-area" @click.stop="onConnectionClick(conn)">
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

        <!-- Temp drag line (canvas coordinates) -->
        <line
          v-if="dragLine.visible"
          :x1="dragLine.x1" :y1="dragLine.y1"
          :x2="dragLine.x2" :y2="dragLine.y2"
          stroke="#4a8eff" stroke-width="2.5"
          stroke-dasharray="8 4"
          style="pointer-events:none"
        />
      </svg>

      <NodeCard
        v-for="node in editorStore.nodes"
        :key="node.id"
        :node="node"
        :step-number="getStepNumber(node.id)"
        :edit-mode="editMode"
        :zoom="currentZoom"
        @select="onNodeSelect"
        @port-drag-start="onPortDragStart"
        @port-click="onPortClick"
        @node-resize="onNodeResize"
      />

      <div v-if="editorStore.nodes.length === 0" class="empty-hint">
        <span class="material-symbols-outlined">dashboard_customize</span>
        <p>从左侧<span class="hl">工具面板</span>拖拽节点到画布</p>
      </div>
    </div>

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

const props = defineProps({ editMode: { type: Boolean, default: false }, detailPanelOpen: { type: Boolean, default: false } })
const emit = defineEmits(['select-node'])

const editorStore = useEditorStore()
const executionStore = useExecutionStore()

const canvasRef = ref(null)
const currentZoom = ref(1.0)
const activeFlowView = ref('all')
const isPanning = ref(false)
const selectedConnId = ref(null)

// ── Per-node height cache (populated by NodeCard @node-resize) ──
const nodeHeights = ref({})

function onNodeResize({ nodeId, height, headerHeight }) {
  if (height === 0) {
    delete nodeHeights.value[nodeId]
    nodeHeights.value = { ...nodeHeights.value }
  } else {
    nodeHeights.value = { ...nodeHeights.value, [nodeId]: { height, headerHeight } }
  }
}

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

function zoomBy(delta) { currentZoom.value = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, currentZoom.value + delta)) }
function resetZoom() { currentZoom.value = 1.0; if (canvasRef.value) { canvasRef.value.scrollLeft = 0; canvasRef.value.scrollTop = 0 } }
function onWheel(e) { zoomBy(e.deltaY > 0 ? -0.05 : 0.05) }

// ── Pan ──
let panStart = { x: 0, y: 0, scrollX: 0, scrollY: 0 }
function onPanStart(e) {
  if (e.button !== 1) return
  e.preventDefault(); isPanning.value = true
  panStart = { x: e.clientX, y: e.clientY, scrollX: canvasRef.value.scrollLeft, scrollY: canvasRef.value.scrollTop }
}
function onPanMove(e) {
  if (!isPanning.value) return
  canvasRef.value.scrollLeft = panStart.scrollX - (e.clientX - panStart.x)
  canvasRef.value.scrollTop = panStart.scrollY - (e.clientY - panStart.y)
}
function onPanEnd() { isPanning.value = false }

onMounted(() => { window.addEventListener('mousemove', onPanMove); window.addEventListener('mouseup', onPanEnd) })
onUnmounted(() => { window.removeEventListener('mousemove', onPanMove); window.removeEventListener('mouseup', onPanEnd) })

// ── Convert screen coords to canvas coords ──
function screenToCanvas(clientX, clientY) {
  const content = canvasRef.value?.querySelector('#canvas-content')
  if (!content) return { x: clientX, y: clientY }
  const rect = content.getBoundingClientRect()
  const zoom = currentZoom.value
  return {
    x: (clientX - rect.left) / zoom,
    y: (clientY - rect.top) / zoom,
  }
}

// ── Connection lines ──
const connectionPaths = computed(() => {
  return editorStore.connections.map((conn) => {
    const fromNode = editorStore.nodes.find((n) => n.id === conn.from_node)
    const toNode = editorStore.nodes.find((n) => n.id === conn.to_node)
    if (!fromNode || !toNode) return null

    const fromPos = getPortCanvasPos(fromNode, conn.from_port, 'output')
    const toPos = getPortCanvasPos(toNode, conn.to_port, 'input')
    if (!fromPos || !toPos) return null

    const fromX = fromPos.x; const fromY = fromPos.y
    const toX = toPos.x; const toY = toPos.y

    // 直接读取 nodeStatuses 保证响应式追踪
    const fromStatus = executionStore.nodeStatuses[conn.from_node]?.status || 'pending'
    const isActive = fromStatus === 'processing'

    let stroke, dash, marker, lineClass, groupClass
    if (conn.type === 'event') {
      stroke = '#adc7ff'; dash = 'none'; marker = 'url(#arrowEvent)'; lineClass = ''; groupClass = 'event-only'
    } else if (isActive) {
      stroke = '#4a8eff'; dash = 'none'; marker = 'url(#arrowDataFlow)'; lineClass = 'flow-line'; groupClass = 'data-only'
    } else {
      stroke = '#4edea3'; dash = '10 5'; marker = 'url(#arrowData)'; lineClass = 'flow-line'; groupClass = 'data-only'
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
      id: conn.id, path, stroke, width: 2.5, dash, marker, lineClass, opacity: 1, groupClass,
      label, labelX, labelY, labelW: label ? label.length * 7 : 0,
      selected: selectedConnId.value === conn.id,
    }
  }).filter(Boolean)
})

function onConnectionClick(conn) {
  if (!props.editMode) return
  selectedConnId.value = selectedConnId.value === conn.id ? null : conn.id
}

// ── Port click ──
function onPortClick({ nodeId, portId, event }) {
  if (!props.editMode) return
  selectedConnId.value = null
}

// ── Port-to-port connection drag ──
const dragLine = ref({ visible: false, x1: 0, y1: 0, x2: 0, y2: 0 })
let connDragFrom = { nodeId: '', portId: '' }

function onPortDragStart({ nodeId, portId, event }) {
  if (!props.editMode) return
  const portEl = event.target?.closest('.io-port')
  if (!portEl || portEl.classList.contains('input-port')) return

  const node = editorStore.nodes.find((n) => n.id === nodeId)
  if (!node) return

  // Start position in canvas coords
  const pos = getPortCanvasPos(node, portId, 'output')
  if (!pos) return

  connDragFrom = { nodeId, portId }
  const startCanvas = screenToCanvas(event.clientX, event.clientY)
  dragLine.value = { visible: true, x1: pos.x, y1: pos.y, x2: startCanvas.x, y2: startCanvas.y }

  const onMove = (ev) => {
    const pt = screenToCanvas(ev.clientX, ev.clientY)
    dragLine.value = { visible: true, x1: pos.x, y1: pos.y, x2: pt.x, y2: pt.y }

    document.querySelectorAll('.io-port.input-port').forEach((el) => {
      const r = el.getBoundingClientRect()
      const over = ev.clientX > r.left - 6 && ev.clientX < r.right + 6 &&
                    ev.clientY > r.top - 6 && ev.clientY < r.bottom + 6
      el.classList.remove('drag-over', 'valid', 'invalid')
      if (over) {
        el.classList.add('drag-over')
        const toN = el.dataset.nodeId; const toP = el.dataset.portId
        el.classList.add(editorStore.arePortsCompatible(nodeId, portId, toN, toP) ? 'valid' : 'invalid')
      }
    })
  }

  const onUp = (ev) => {
    dragLine.value.visible = false
    document.querySelectorAll('.io-port').forEach((el) => el.classList.remove('drag-over', 'valid', 'invalid'))

    const target = document.elementFromPoint(ev.clientX, ev.clientY)
    const tgtPort = target?.closest('.io-port.input-port')
    if (tgtPort) {
      const toN = tgtPort.dataset.nodeId; const toP = tgtPort.dataset.portId
      if (toN && toP && toN !== nodeId && editorStore.arePortsCompatible(nodeId, portId, toN, toP)) {
        const pf = editorStore.getPortDef(node, portId, 'output')
        editorStore.createConnection(nodeId, portId, toN, toP, pf?.data_type === 'event' ? 'event' : 'data')
      }
    }
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

// ── Port helpers ──
function getPortCanvasPos(node, portId, side) {
  const tdef = editorStore.getNodeTypeDef(node.type)
  if (!tdef) return null
  const ports = side === 'input' ? tdef.ports?.inputs : tdef.ports?.outputs
  const total = ports?.length || 0
  const idx = ports?.findIndex((p) => p.id === portId) ?? -1
  const w = getNodeWidth(node)

  // Per-instance persisted position (user drag)
  const saved = node.config?._port_positions?.[portId]
  if (saved?.top != null) {
    return {
      x: side === 'input' ? node.position.x : node.position.x + w,
      y: node.position.y + saved.top + 7,
    }
  }

  let top
  const hi = nodeHeights.value[node.id]
  if (hi && idx >= 0 && total > 0) {
    const available = Math.max(hi.height - 14 - hi.headerHeight, 1)
    top = Math.round(hi.headerHeight + available * (idx + 1) / (total + 1))
  } else {
    const hasTabs = (tdef.tabs?.length || 0) > 0
    const estH = hasTabs ? 105 : 85
    const estHeader = hasTabs ? 57 : 33
    const estAvail = Math.max(estH - 14 - estHeader, 1)
    top = idx >= 0 && total > 0
      ? Math.round(estHeader + estAvail * (idx + 1) / (total + 1))
      : Math.round(estHeader + estAvail / 2)
  }

  return {
    x: side === 'input' ? node.position.x : node.position.x + w,
    y: node.position.y + top + 7,
  }
}

function getPortLabel(node, portId) {
  const tdef = editorStore.getNodeTypeDef(node.type)
  return tdef?.ports?.outputs?.find((p) => p.id === portId)?.label || ''
}

function getNodeWidth(node) {
  const m = { input_image: 220, ocr: 220, tts: 220, ts_output: 220, ts_input: 220, context_build: 250, llm: 250, stt_history: 280, stt_listen: 320 }
  return m[node.type] || 250
}

function getStepNumber(nodeId) {
  const idx = editorStore.nodes.findIndex((n) => n.id === nodeId)
  return idx >= 0 ? String.fromCharCode(0x2460 + idx) : ''
}

function onNodeSelect(node) { emit('select-node', node.id) }

// ── Keyboard ──
function onKeydown(e) {
  if (!props.editMode) return
  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedConnId.value) {
    e.preventDefault(); editorStore.deleteConnection(selectedConnId.value); selectedConnId.value = null
  }
  if (e.key === 'Escape') selectedConnId.value = null
}
onMounted(() => { window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('keydown', onKeydown) })
</script>

<style scoped>
.pipeline-canvas {
  flex: 1; margin-left: 256px; position: relative;
  background: #121417; overflow: auto; height: calc(100vh - 88px);
  transition: margin-right 0.2s ease;
}
.pipeline-canvas.detail-open { margin-right: 320px; }
.pipeline-canvas.is-panning { cursor: grabbing; user-select: none; }
.canvas-grid {
  position: absolute; top: 0; left: 0; z-index: 0; pointer-events: none; opacity: 0.15;
  background-image: linear-gradient(#31353d 1px, transparent 1px), linear-gradient(90deg, #31353d 1px, transparent 1px);
}
.canvas-content { position: relative; z-index: 10; padding: 32px; transition: transform 0.2s ease; }
.flow-view[data-flow="data"] .event-only { display: none !important; }
.flow-view[data-flow="event"] .data-only { display: none !important; }
.connections-svg { position: absolute; top: 0; left: 0; pointer-events: none; z-index: 0; }
.conn-hit-area { pointer-events: stroke; cursor: pointer; }
.flow-line { animation: flowDash 1.0s linear infinite; }
@keyframes flowDash { to { stroke-dashoffset: -24; } }
.empty-hint {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; pointer-events: none; z-index: 20;
  color: rgba(139, 144, 160, 0.4); font-size: 13px; gap: 8px;
}
.empty-hint .material-symbols-outlined { font-size: 48px; opacity: 0.3; }
.empty-hint .hl { color: rgba(173, 199, 255, 0.5); }
.pipeline-canvas::-webkit-scrollbar { width: 6px; height: 6px; }
.pipeline-canvas::-webkit-scrollbar-track { background: #10131b; }
.pipeline-canvas::-webkit-scrollbar-thumb { background: #31353d; border-radius: 3px; }
.pipeline-canvas::-webkit-scrollbar-thumb:hover { background: #414754; }
</style>
