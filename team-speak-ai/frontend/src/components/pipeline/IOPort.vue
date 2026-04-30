<template>
  <div
    class="io-port"
    :class="[
      side === 'left' ? 'input-port' : 'output-port',
      portState,
    ]"
    :data-node-id="dataNodeId"
    :data-port-id="dataPortId"
    :data-data-type="dataType"
    :style="{ top: position + 'px' }"
    @mouseenter="showLabel = true"
    @mouseleave="showLabel = false"
    @mousedown.stop="onMouseDown"
    @click.stop="onClick"
  >
    <span class="io-label" :class="{ visible: showLabel }">{{ label }}</span>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'
import { useEditorStore } from '@/stores/editor.js'

const props = defineProps({
  side: { type: String, required: true },
  position: { type: Number, required: true },
  label: { type: String, default: '' },
  portState: { type: String, default: 'disconnected' },
  dataType: { type: String, default: '' },
  dataNodeId: { type: String, default: '' },
  dataPortId: { type: String, default: '' },
  editMode: { type: Boolean, default: false },
})

const emit = defineEmits(['portDragStart', 'portClick'])
const showLabel = ref(false)
const editorStore = useEditorStore()

let dragStartX = 0
let dragStartY = 0
let hasDragged = false

function onMouseDown(e) {
  if (!props.editMode) return
  dragStartX = e.clientX
  dragStartY = e.clientY
  hasDragged = false

  // Start listening for moves
  const onMove = (ev) => {
    const dx = Math.abs(ev.clientX - dragStartX)
    const dy = Math.abs(ev.clientY - dragStartY)
    if (dx > 3 || dy > 3) {
      hasDragged = true
      // If output port, emit drag start for connection wiring
      if (props.side === 'right') {
        emit('portDragStart', e)
      }
      // Vertical port position drag
      if (dy > 5 && Math.abs(ev.clientY - dragStartY) > Math.abs(ev.clientX - dragStartX)) {
        doVerticalDrag(e, ev)
      }
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }

  const onUp = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function doVerticalDrag(startEvent, moveEvent) {
  const portEl = startEvent.target.closest('.io-port')
  const nodeEl = portEl?.closest('.node-card')
  if (!nodeEl) return

  const nodeRect = nodeEl.getBoundingClientRect()
  const startTop = parseInt(portEl.style.top) || props.position
  const startY = moveEvent.clientY

  const onMove = (ev) => {
    const deltaY = ev.clientY - startY
    const newTop = Math.max(28, Math.min(nodeRect.height - 20, startTop + deltaY))
    portEl.style.top = newTop + 'px'
  }

  const onUp = (ev) => {
    const finalTop = parseInt(portEl.style.top) || startTop
    portEl.style.top = finalTop + 'px'
    // Persist port position change
    if (props.dataNodeId && props.dataPortId) {
      pipelineSocket.sendCommand(editorStore.flowId, 'port.move', {
        node_id: props.dataNodeId,
        port_id: props.dataPortId,
        side: props.side,
        position: finalTop,
      }).catch(() => {})
    }
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onClick(e) {
  if (!props.editMode) return
  // Only emit click if not dragged
  if (!hasDragged) {
    emit('portClick', e)
  }
  hasDragged = false
}
</script>

<style scoped>
.io-port {
  position: absolute;
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2.5px solid #8b90a0;
  background: #10131b;
  z-index: 35;
  cursor: pointer;
  transition: all 0.2s ease;
}

.io-port.input-port  { left: -7px; }
.io-port.output-port { right: -7px; }

.io-port:hover { transform: scale(1.5); z-index: 60; }

.io-port.disconnected {
  border-color: #8b90a0;
  background: #10131b;
  box-shadow: none;
}

.io-port.connected {
  border-color: #4edea3;
  background: rgba(78, 222, 163, 0.12);
  box-shadow: 0 0 8px rgba(78, 222, 163, 0.3);
}

.io-port.flowing {
  border-color: #4a8eff;
  background: rgba(74, 142, 255, 0.18);
  box-shadow: 0 0 12px rgba(74, 142, 255, 0.5);
  animation: portFlowPulse 1.2s ease-in-out infinite;
}

.io-port.drag-over { transform: scale(1.8); z-index: 65; }
.io-port.drag-over.valid {
  border-color: #4edea3;
  background: rgba(78, 222, 163, 0.3);
  box-shadow: 0 0 16px rgba(78, 222, 163, 0.6);
}
.io-port.drag-over.invalid {
  border-color: #ffb4ab;
  background: rgba(255, 180, 171, 0.3);
  box-shadow: 0 0 16px rgba(255, 180, 171, 0.6);
}

@keyframes portFlowPulse {
  0%, 100% { box-shadow: 0 0 6px rgba(74, 142, 255, 0.5); }
  50% { box-shadow: 0 0 18px rgba(74, 142, 255, 0.85); }
}

.io-label {
  position: absolute;
  font-size: 9px;
  font-family: 'Space Grotesk', sans-serif;
  white-space: nowrap;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  color: #c1c6d7;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  background: rgba(11, 14, 22, 0.95);
  padding: 3px 7px;
  border-radius: 3px;
  border: 1px solid #31353d;
  z-index: 50;
}

.io-label.visible { opacity: 1; pointer-events: auto; }

.io-port.output-port .io-label {
  left: auto; right: 0;
  transform: translateX(0);
}
</style>
