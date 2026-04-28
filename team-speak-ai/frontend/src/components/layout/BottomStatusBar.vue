<template>
  <footer class="status-bar">
    <div class="status-items">
      <div v-for="svc in displayServices" :key="svc.id" class="status-item">
        <div class="status-dot" :class="svc.status"></div>
        <span class="status-label">{{ svc.name }}:</span>
        <span :class="`status-value status-${svc.status}`">{{ svc.label }}</span>
      </div>
    </div>
    <div class="status-links">
      <a href="#" class="status-link">API参考</a>
      <a href="#" class="status-link">文档</a>
      <a href="#" class="status-link">支持</a>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useConnectionStore } from '@/stores/connection.js'
import { useExecutionStore } from '@/stores/execution.js'

const connectionStore = useConnectionStore()
const executionStore = useExecutionStore()

const statusConfig = {
  connected: '运行中',
  healthy: '最佳',
  listening: 'STT 监听中',
  connecting: '重连中',
  disconnected: '断开',
  error: '异常',
  unknown: '未知',
}

const displayServices = computed(() => {
  const services = [...connectionStore.services]
  // 动态更新 pipeline 状态
  const pipeline = services.find((s) => s.id === 'pipeline')
  if (pipeline && executionStore.status === 'running') {
    pipeline.status = 'listening'
    pipeline.label = '运行中'
  }
  return services.slice(0, 3).map((s) => ({
    ...s,
    label: s.label || statusConfig[s.status] || s.status,
  }))
})
</script>

<style scoped>
.status-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 50;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 32px;
  background: #020617;
  border-top: 1px solid rgba(65, 71, 84, 0.5);
  font-family: 'Inter', sans-serif;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
}

.status-items {
  display: flex;
  align-items: center;
  gap: 24px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.connected,
.status-dot.healthy {
  background: #4edea3;
  box-shadow: 0 0 8px rgba(78, 222, 163, 0.6);
  animation: statusPulse 2s ease-in-out infinite;
}

.status-dot.listening {
  background: #adc7ff;
  box-shadow: 0 0 8px rgba(173, 199, 255, 0.6);
  animation: statusPulse 2s ease-in-out infinite;
}

.status-dot.connecting {
  background: #fbbf24;
  box-shadow: 0 0 6px rgba(251, 191, 36, 0.4);
  animation: statusPulse 1s ease-in-out infinite;
}

.status-dot.disconnected {
  background: #ef4444;
}

.status-dot.error {
  background: #ffb4ab;
  box-shadow: 0 0 8px rgba(255, 180, 171, 0.6);
  animation: statusPulse 1s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-label {
  color: #94a3b8;
  font-weight: 500;
}

.status-value { font-weight: 500; }

.status-connected, .status-healthy { color: #4edea3; }
.status-listening { color: #adc7ff; }
.status-connecting { color: #fbbf24; }
.status-disconnected { color: #ef4444; }
.status-error { color: #ffb4ab; }

.status-links { display: flex; gap: 16px; }

.status-link {
  color: #64748b;
  text-decoration: none;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.status-link:hover {
  color: #93c5fd;
  opacity: 1;
}
</style>
