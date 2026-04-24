<template>
  <div class="layout">
    <!-- ═══ Header ═══ -->
    <header class="header">
      <div class="h-left">
        <svg class="h-logo" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#e94560" stroke-width="1.8">
          <circle cx="12" cy="12" r="10"/>
          <path d="M7 12 L10 15 L17 9" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="h-title">TeamSpeak AI</span>
      </div>
      <div class="h-right">
        <span class="h-badge" :class="{ on: connected }">
          <span class="h-dot"></span>
          {{ connected ? '已连接' : '未连接' }}
        </span>
      </div>
    </header>

    <!-- ═══ Body ═══ -->
    <div class="body">
      <!-- ── Sidebar ── -->
      <aside class="sidebar">
        <div class="sb-head">
          <span class="sb-title">功能列表</span>
          <span class="sb-badge" v-if="totalFeatures">{{ totalFeatures }}</span>
        </div>

        <div v-if="sidebarStore.groups.length === 0" class="sb-loading">
          <span>加载中...</span>
        </div>

        <nav class="sb-nav" v-else>
          <template v-for="group in sidebarStore.groups" :key="group.id">
            <div class="sb-group" @click="sidebarStore.toggleGroup(group.id)">
              <svg class="sb-arrow" :class="{ open: sidebarStore.expandedGroups.has(group.id) }" viewBox="0 0 16 16" width="10" height="10">
                <path d="M6 4 L10 8 L6 12" fill="currentColor"/>
              </svg>
              <span class="sb-gname">{{ group.name }}</span>
            </div>
            <div class="sb-items" v-if="sidebarStore.expandedGroups.has(group.id)">
              <button
                v-for="feat in group.children" :key="feat.id"
                class="sb-item"
                :class="{ active: activeFeatureId === feat.id }"
                @click="selectFeature(feat.id)"
              >
                <span class="sb-ico">{{ feat.icon || '📋' }}</span>
                <span class="sb-lbl">{{ feat.name }}</span>
                <span class="sb-run" v-if="featureRunning(feat.id)" title="运行中"></span>
              </button>
            </div>
          </template>
        </nav>
      </aside>

      <!-- ── Content ── -->
      <main class="content">
        <FeaturePage :feature-id="activeFeatureId" />
      </main>
    </div>

    <!-- ═══ Footer ═══ -->
    <footer class="footer">
      <div class="ft-head">
        <span class="ft-title">事件日志</span>
        <span class="ft-count" v-if="recentEvents.length">{{ recentEvents.length }}</span>
      </div>
      <div class="ft-log">
        <div v-for="(evt, i) in recentEvents" :key="evt.id || i" class="ft-item" :class="evt.type">
          <span class="ft-time">{{ fmt(evt.timestamp) }}</span>
          <span class="ft-badge" :class="evt.type">{{ evt.type }}</span>
          <span class="ft-msg">{{ evt.title }} {{ evt.content }}</span>
        </div>
        <div v-if="recentEvents.length === 0" class="ft-item ft-empty">
          <span class="ft-msg">— 等待事件 —</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSidebarStore } from '@/stores/sidebar'
import { usePipelineStore } from '@/stores/pipeline'
import { pipelineSocket } from '@/api/pipeline'
import FeaturePage from '@/views/FeaturePage.vue'

const sidebarStore = useSidebarStore()
const pipelineStore = usePipelineStore()

const activeFeatureId = ref(null)
const connected = ref(false)

const recentEvents = computed(() => pipelineStore.importantEvents.slice(0, 30))
const totalFeatures = computed(() => sidebarStore.groups.reduce((s, g) => s + g.children.length, 0))
const featureRunning = (id) => pipelineStore.features[id]?.status === 'running'
const selectFeature = (id) => { activeFeatureId.value = id; sidebarStore.setActive(id) }
const fmt = (ts) => ts ? new Date(ts).toLocaleTimeString() : ''

onMounted(() => {
  pipelineSocket.on('connected', () => { connected.value = true; pipelineSocket.send('get_config') })
  pipelineSocket.on('disconnected', () => { connected.value = false })
  pipelineSocket.on('feature_config', (cfgs) => {
    if (Array.isArray(cfgs)) {
      cfgs.forEach((c) => pipelineStore.registerFeature(c))
      sidebarStore.loadFromConfig(cfgs)
      if (!activeFeatureId.value && cfgs.length > 0) activeFeatureId.value = cfgs[0].id
    }
  })
  pipelineSocket.on('pipeline_start', (d) => pipelineStore.handlePipelineStart(d))
  pipelineSocket.on('pipeline_complete', (d) => pipelineStore.handlePipelineComplete(d))
  pipelineSocket.on('pipeline_state', (d) => pipelineStore.handlePipelineState(d))
  pipelineSocket.on('node_update', (d) => pipelineStore.handleNodeUpdate(d))
  pipelineSocket.on('node_complete', (d) => pipelineStore.handleNodeComplete(d))
  pipelineSocket.on('node_error', (d) => pipelineStore.handleNodeError(d))
  pipelineSocket.on('important_update', (d) => pipelineStore.handleImportantUpdate(d))
  pipelineSocket.connect()
})
onUnmounted(() => pipelineSocket.disconnect())
</script>

<style scoped>
.layout {
  display: flex; flex-direction: column;
  height: 100vh;
  background: #080c14;
  color: rgba(255,255,255,0.85);
}

/* ── Header ── */
.header {
  display: flex; align-items: center; justify-content: space-between;
  height: 44px; padding: 0 16px;
  background: rgba(8,12,20,0.95);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(8px);
  z-index: 10; flex-shrink: 0;
}
.h-left { display: flex; align-items: center; gap: 8px; }
.h-logo { flex-shrink: 0; }
.h-title {
  font-size: 0.85rem; font-weight: 700;
  background: linear-gradient(135deg, #e94560, #f97316);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.h-right { display: flex; align-items: center; gap: 8px; }
.h-badge {
  display: flex; align-items: center; gap: 5px;
  font-size: 0.65rem;
  padding: 2px 10px; border-radius: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.3);
}
.h-badge.on {
  background: rgba(52,211,153,0.08);
  border-color: rgba(52,211,153,0.15);
  color: #6ee7b7;
}
.h-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #555;
  transition: all 0.3s;
}
.h-badge.on .h-dot {
  background: #34d399;
  box-shadow: 0 0 4px rgba(52,211,153,0.5);
}

/* ── Body ── */
.body { display: flex; flex: 1; overflow: hidden; }

/* ── Sidebar ── */
.sidebar {
  width: 200px; flex-shrink: 0;
  background: rgba(8,12,20,0.5);
  border-right: 1px solid rgba(255,255,255,0.05);
  display: flex; flex-direction: column;
}
.sb-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 12px 8px;
}
.sb-title {
  font-size: 0.62rem; text-transform: uppercase;
  letter-spacing: 1px; color: rgba(255,255,255,0.25);
}
.sb-badge {
  font-size: 0.58rem;
  background: rgba(255,255,255,0.04);
  padding: 1px 6px; border-radius: 6px;
  color: rgba(255,255,255,0.25);
}
.sb-loading {
  padding: 24px 12px; text-align: center;
  font-size: 0.72rem; color: rgba(255,255,255,0.15);
}
.sb-nav { flex: 1; overflow-y: auto; padding: 0 6px 12px; }
.sb-group {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; cursor: pointer;
  color: rgba(255,255,255,0.35); font-size: 0.7rem;
  transition: color 0.15s; user-select: none;
}
.sb-group:hover { color: rgba(255,255,255,0.65); }
.sb-arrow { transition: transform 0.2s; opacity: 0.5; }
.sb-arrow.open { transform: rotate(90deg); }
.sb-gname { flex: 1; }

.sb-items { display: flex; flex-direction: column; gap: 1px; }
.sb-item {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 8px 7px 22px;
  background: none; border: none; border-radius: 6px;
  color: rgba(255,255,255,0.55); cursor: pointer;
  font-size: 0.72rem; text-align: left;
  transition: all 0.15s;
}
.sb-item:hover { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.85); }
.sb-item.active {
  background: rgba(233,69,96,0.12);
  color: #e94560;
}
.sb-ico { font-size: 0.85rem; flex-shrink: 0; }
.sb-lbl { flex: 1; }
.sb-run {
  width: 5px; height: 5px; border-radius: 50%;
  background: #34d399;
  animation: dotPulse 1s ease-in-out infinite;
}

/* ── Content ── */
.content {
  flex: 1; padding: 14px 18px;
  overflow-y: auto; overflow-x: hidden;
}

/* ── Footer ── */
.footer {
  height: 72px; flex-shrink: 0;
  background: rgba(8,12,20,0.8);
  border-top: 1px solid rgba(255,255,255,0.04);
  display: flex; flex-direction: column;
}
.ft-head {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.02);
}
.ft-title {
  font-size: 0.58rem; text-transform: uppercase;
  letter-spacing: 0.5px; color: rgba(255,255,255,0.2);
}
.ft-count {
  font-size: 0.52rem;
  background: rgba(255,255,255,0.03);
  padding: 0 5px; border-radius: 4px;
  color: rgba(255,255,255,0.2);
}
.ft-log { flex: 1; overflow-y: auto; padding: 3px 14px; }
.ft-item {
  display: flex; align-items: center; gap: 6px;
  padding: 1px 0; font-size: 0.65rem;
  font-family: ui-monospace, 'Cascadia Code', monospace;
}
.ft-time { color: rgba(255,255,255,0.15); flex-shrink: 0; }
.ft-badge {
  font-size: 0.52rem; padding: 0 4px; border-radius: 3px;
  text-transform: uppercase; flex-shrink: 0;
}
.ft-badge.info { background: rgba(56,189,248,0.1); color: #38bdf8; }
.ft-badge.warning { background: rgba(251,191,36,0.1); color: #fbbf24; }
.ft-badge.error { background: rgba(239,68,68,0.1); color: #ef4444; }
.ft-msg { color: rgba(255,255,255,0.3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ft-empty .ft-msg { color: rgba(255,255,255,0.08); }

@keyframes dotPulse {
  0%,100%{opacity:1;transform:scale(1)}
  50%{opacity:0.4;transform:scale(1.4)}
}
</style>
