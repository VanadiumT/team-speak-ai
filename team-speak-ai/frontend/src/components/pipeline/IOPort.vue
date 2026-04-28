<template>
  <div
    class="io-port"
    :class="[
      side === 'left' ? 'input-port' : 'output-port',
      portState,
      { 'data-only': true }
    ]"
    :style="{ top: position + 'px' }"
    @mouseenter="showLabel = true"
    @mouseleave="showLabel = false"
  >
    <span v-if="showLabel" class="io-label">{{ label }}</span>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  side: { type: String, required: true },   // 'left' | 'right'
  position: { type: Number, required: true }, // top offset in px
  label: { type: String, default: '' },
  portState: { type: String, default: 'disconnected' }, // 'disconnected' | 'connected' | 'flowing'
})

const showLabel = ref(false)
</script>

<style scoped>
.io-port {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2.5px solid #8b90a0;
  background: #10131b;
  z-index: 35;
  cursor: pointer;
  transition: all 0.2s ease;
}

.io-port.input-port  { left: -7px; }
.io-port.output-port { right: -7px; }

.io-port:hover {
  transform: scale(1.5);
  z-index: 60;
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
  background: rgba(11, 14, 22, 0.95);
  padding: 3px 7px;
  border-radius: 3px;
  border: 1px solid #31353d;
  z-index: 50;
}

.io-port.output-port .io-label {
  left: auto;
  right: 0;
  transform: translateX(0);
}
</style>
