<template>
  <div class="canvas-controls">
    <!-- Flow view toggles -->
    <button
      v-for="mode in viewModes"
      :key="mode.value"
      class="flow-toggle-btn"
      :class="{ active: activeView === mode.value }"
      @click="$emit('update:activeView', mode.value)"
      :title="mode.title"
    >
      <span class="material-symbols-outlined toggle-icon">{{ mode.icon }}</span>
      {{ mode.label }}
    </button>

    <div class="divider"></div>

    <!-- Zoom out -->
    <button class="zoom-btn" @click="$emit('zoom', -0.1)" title="缩小">
      <span class="material-symbols-outlined">remove</span>
    </button>

    <!-- Zoom percentage -->
    <input
      class="zoom-input"
      type="text"
      :value="Math.round(zoom * 100) + '%'"
      @focus="$event.target.select()"
      @change="onZoomInput"
      @keydown.enter="onZoomInput"
    />

    <!-- Zoom in -->
    <button class="zoom-btn" @click="$emit('zoom', 0.1)" title="放大">
      <span class="material-symbols-outlined">add</span>
    </button>

    <div class="divider"></div>

    <!-- Fit screen -->
    <button class="zoom-btn" @click="$emit('resetZoom')" title="适应屏幕">
      <span class="material-symbols-outlined">fullscreen_exit</span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  zoom: { type: Number, default: 1.0 },
  activeView: { type: String, default: 'all' },
})

const emit = defineEmits(['update:activeView', 'zoom', 'resetZoom'])

const viewModes = [
  { value: 'all', label: '全部', icon: 'layers', title: '显示全部信息' },
  { value: 'data', label: '数据流', icon: 'cable', title: '显示数据流 (IO端口 + 数据类型)' },
  { value: 'event', label: '事件流', icon: 'schedule', title: '显示事件流 (触发顺序)' },
]

function onZoomInput(event) {
  let num = parseFloat(event.target.value.replace('%', '')) / 100
  if (isNaN(num)) return
  num = Math.max(0.25, Math.min(3.0, num))
  event.target.value = Math.round(num * 100) + '%'
  emit('zoom', num - props.zoom)
}
</script>

<style scoped>
.canvas-controls {
  position: fixed;
  z-index: 50;
  left: 272px;
  bottom: 48px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px;
  background: rgba(2, 6, 23, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(65, 71, 84, 0.5);
  border-radius: 8px;
}

.flow-toggle-btn {
  padding: 4px 10px;
  font-size: 10px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: #8b90a0;
  cursor: pointer;
  border-radius: 4px;
  border: none;
  background: transparent;
  transition: color 0.2s, background 0.2s;
  display: flex;
  align-items: center;
  gap: 2px;
}

.flow-toggle-btn:hover {
  color: #c1c6d7;
  background: rgba(255, 255, 255, 0.05);
}

.flow-toggle-btn.active {
  color: #adc7ff;
  background: rgba(173, 199, 255, 0.12);
  font-weight: 600;
}

.toggle-icon {
  font-size: 14px;
}

.divider {
  width: 1px;
  height: 20px;
  background: rgba(65, 71, 84, 0.5);
  margin: 0 6px;
}

.zoom-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.zoom-btn:hover {
  color: #60a5fa;
  background: rgba(30, 41, 59, 0.5);
}

.zoom-btn:active {
  transform: scale(0.9);
}

.zoom-btn .material-symbols-outlined {
  font-size: 18px;
}

.zoom-input {
  width: 48px;
  background: transparent;
  border: none;
  font-size: 12px;
  font-family: 'Space Grotesk', sans-serif;
  text-align: center;
  color: #adc7ff;
  cursor: pointer;
  padding: 0;
}

.zoom-input:focus {
  outline: none;
}
</style>
