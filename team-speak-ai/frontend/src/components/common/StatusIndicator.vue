<template>
  <div class="status-indicator">
    <span class="status-dot" :class="{ connected }"></span>
    <span class="status-label">{{ label }}</span>
  </div>
</template>

<script setup>
defineProps({
  connected: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: 'Status',
  },
})
</script>

<style scoped>
.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f44336;
  transition: background 0.3s;
}

.status-dot.connected {
  background: #4caf50;
}

.status-label {
  color: #888;
}
</style>
