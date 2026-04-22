<template>
  <div class="layout">
    <header class="header">
      <div class="header-title">TeamSpeak AI</div>
      <div class="header-actions">
        <StatusIndicator :connected="appStore.teamspeakConnected" label="TeamSpeak" />
        <StatusIndicator :connected="appStore.connected" label="WebSocket" />
        <button class="settings-btn" @click="showSettings = !showSettings">
          ⚙️
        </button>
      </div>
    </header>

    <div class="main-container">
      <aside class="sidebar">
        <div class="sidebar-title">功能列表</div>
        <nav class="nav-list">
          <button
            v-for="item in menuItems"
            :key="item.id"
            class="nav-item"
            :class="{ active: activeMenu === item.id }"
            @click="activeMenu = item.id"
          >
            {{ item.name }}
          </button>
        </nav>
      </aside>

      <main class="content">
        <div v-if="activeMenu === 'arena_championship'" class="feature-panel">
          <h2>竞技场锦标赛</h2>
          <FileUploader function-id="arena_championship" />
        </div>
        <div v-else-if="activeMenu === 'darkzone'" class="feature-panel">
          <h2>暗区</h2>
          <FileUploader function-id="darkzone" />
        </div>
        <div v-else class="feature-panel">
          <h2>欢迎使用 TeamSpeak AI</h2>
          <p>请从左侧选择一个功能</p>
        </div>
      </main>
    </div>

    <footer class="footer">
      <div class="log-container">
        <div v-for="(log, i) in logs" :key="i" class="log-item" :class="log.type">
          [{{ log.time }}] {{ log.message }}
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import StatusIndicator from '@/components/common/StatusIndicator.vue'
import FileUploader from '@/components/common/FileUploader.vue'

const appStore = useAppStore()

const showSettings = ref(false)
const activeMenu = ref(null)
const logs = ref([])

const menuItems = [
  { id: 'arena_championship', name: '🏆 锦标赛' },
  { id: 'darkzone', name: '🌑 暗区' },
]

const addLog = (message, type = 'info') => {
  const time = new Date().toLocaleTimeString()
  logs.value.unshift({ time, message, type })
  if (logs.value.length > 50) {
    logs.value.pop()
  }
}

onMounted(() => {
  appStore.initWebSocket()
  addLog('Frontend initialized')
})

onUnmounted(() => {
  appStore.disconnect()
})
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.header-title {
  font-size: 1.5rem;
  font-weight: bold;
  color: #e94560;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.settings-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 5px;
}

.settings-btn:hover {
  opacity: 0.7;
}

.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 240px;
  background: #16213e;
  border-right: 1px solid #0f3460;
  padding: 20px;
}

.sidebar-title {
  font-size: 0.9rem;
  color: #888;
  margin-bottom: 15px;
  text-transform: uppercase;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  padding: 12px 15px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #eaeaea;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #0f3460;
}

.nav-item.active {
  background: #e94560;
  color: white;
}

.content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

.feature-panel h2 {
  margin-bottom: 20px;
  color: #e94560;
}

.footer {
  height: 120px;
  background: #0f0f23;
  border-top: 1px solid #0f3460;
  padding: 10px 20px;
}

.log-container {
  height: 100%;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.85rem;
}

.log-item {
  padding: 4px 0;
  color: #888;
}

.log-item.info {
  color: #4fc3f7;
}

.log-item.error {
  color: #f44336;
}

.log-item.success {
  color: #4caf50;
}
</style>
