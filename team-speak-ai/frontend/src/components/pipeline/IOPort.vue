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

// ── Direction-locked drag state machine ──
// idle → tracking → vertical | horizontal | click
let dragState = 'idle'
let startX = 0, startY = 0, startTop = 0

function onMouseDown(e) {
  if (e.button !== 0) return
  const portEl = e.currentTarget
  const nodeEl = portEl.closest('.node-card')
  if (!nodeEl) return

  startX = e.clientX
  startY = e.clientY
  startTop = parseInt(portEl.style.top) || props.position
  dragState = 'tracking'

  function onMove(ev) {
    if (dragState === 'horizontal' || dragState === 'idle') return

    const dx = ev.clientX - startX
    const dy = ev.clientY - startY
    const dist = Math.abs(dx) + Math.abs(dy)

    if (dragState === 'tracking' && dist >= 4) {
      const isOutput = props.side === 'right'
      // Output port with rightward movement → connection wiring
      if (isOutput && dx > 2 && dx > Math.abs(dy)) {
        dragState = 'horizontal'
        emit('portDragStart', ev)
        cleanup()
        return
      }
      // Otherwise → vertical reposition
      dragState = 'vertical'
      portEl.style.transition = 'none'
    }

    if (dragState === 'vertical') {
      if (!props.editMode) return
      const nodeRect = nodeEl.getBoundingClientRect()
      const headerEl = nodeEl.querySelector('.node-header')
      const tabBarEl = nodeEl.querySelector('.node-tab-bar')
      let minTop = 4
      if (headerEl) minTop = Math.round(headerEl.getBoundingClientRect().height)
      if (tabBarEl) minTop += Math.round(tabBarEl.getBoundingClientRect().height)
      minTop += 6
      const maxTop = nodeRect.height - 11
      const newTop = Math.max(minTop, Math.min(maxTop, startTop + dy))
      portEl.style.top = newTop + 'px'

      // Show / update range track on first vertical frame
      if (!nodeEl.querySelector('.port-drag-track')) {
        const track = document.createElement('div')
        track.className = 'port-drag-track'
        track.style.cssText = [
          'position: absolute', 'width: 2px', 'border-radius: 1px',
          'background: rgba(173,199,255,0.35)', 'pointer-events: none', 'z-index: 34',
          `top: ${minTop}px`, `height: ${maxTop - minTop}px`,
          props.side === 'left' ? 'left: 2px' : 'right: 2px',
        ].join(';')
        nodeEl.appendChild(track)
      }

      // Pulse when hitting boundary
      const atBoundary = newTop <= minTop + 1 || newTop >= maxTop - 1
      if (atBoundary) {
        if (!portEl.classList.contains('at-boundary')) {
          portEl.classList.add('at-boundary')
          setTimeout(() => portEl.classList.remove('at-boundary'), 300)
        }
      }
    }
  }

  function onUp(ev) {
    if (dragState === 'tracking') {
      emit('portClick', ev)
    }
    if (dragState === 'vertical') {
      portEl.style.transition = ''
      const finalTop = parseInt(portEl.style.top) || startTop
      if (props.editMode && props.dataNodeId && props.dataPortId) {
        const node = editorStore.nodes.find(n => n.id === props.dataNodeId)
        if (node) {
          if (!node.config) node.config = {}
          if (!node.config._port_positions) node.config._port_positions = {}
          node.config._port_positions[props.dataPortId] = { side: props.side, top: finalTop }
        }
        pipelineSocket.sendCommand(editorStore.flowId, 'port.move', {
          node_id: props.dataNodeId,
          port_id: props.dataPortId,
          side: props.side,
          position: finalTop,
        }).catch(() => {})
      }
    }
    dragState = 'idle'
    cleanup()
  }

  function cleanup() {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    const track = nodeEl.querySelector('.port-drag-track')
    if (track) track.remove()
    portEl.classList.remove('at-boundary')
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
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

/* Event ports: diamond shape (rotated square) */
.io-port[data-data-type="event"] {
  border-radius: 2px;
  transform: rotate(45deg);
  width: 12px; height: 12px;
}
.io-port[data-data-type="event"]:hover {
  transform: rotate(45deg) scale(1.5);
}
.io-port[data-data-type="event"].disconnected {
  border-color: rgba(173, 199, 255, 0.45);
}
.io-port[data-data-type="event"].connected {
  border-color: #adc7ff;
  background: rgba(173, 199, 255, 0.15);
  box-shadow: 0 0 8px rgba(173, 199, 255, 0.35);
}
.io-port[data-data-type="event"].flowing {
  border-color: #ffb695;
  background: rgba(255, 182, 149, 0.22);
  box-shadow: 0 0 14px rgba(255, 182, 149, 0.6);
}

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

/* Boundary pulse when port hits min/max edge */
.io-port.at-boundary {
  box-shadow: 0 0 12px rgba(255, 182, 149, 0.7);
  border-color: #ffb695;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
</style>
